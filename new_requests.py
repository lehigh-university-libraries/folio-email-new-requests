import json
import logging
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path

import yaml
from folioclient import FolioClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)

FIELD_LABELS = {
    "requestDate": "Request Date",
    "requester.barcode": "Patron Barcode",
    "item.barcode": "Item Barcode",
    "instance.title": "Title",
    "item.callNumber": "Call Number",
    "requestType": "Request Type",
    "patronComments": "Comments",
}

DIVIDER = "─" * 46


def load_config(path: str) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        log.error("Config file not found: %s", path)
        sys.exit(1)
    with config_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_state(path: str) -> str | None:
    state_path = Path(path)
    if not state_path.exists():
        return None
    with state_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("last_request_date")


def save_state(path: str, date_str: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"last_request_date": date_str}, f)


def build_cql_query(last_date: str | None) -> str:
    base = 'status=="Open - Not yet filled"'
    if last_date:
        base = f'{base} AND requestDate > "{last_date}"'
    return f"({base}) sortby requestDate"


def fetch_new_requests(fc: FolioClient, query: str, limit: int) -> list:
    log.info("Querying FOLIO: %s", query)
    return list(fc.folio_get_all("/circulation/requests", key="requests", query=query, limit=limit))


def get_field_value(request: dict, dotted_path: str):
    value = request
    for part in dotted_path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def group_by_service_point(requests: list) -> dict:
    groups: dict[str, list] = {}
    for req in requests:
        service_point = get_field_value(req, "pickupServicePoint.name") or req.get("pickupServicePointId", "Unknown")
        groups.setdefault(service_point, []).append(req)
    return groups


def format_request_block(request: dict, fields: list) -> str:
    lines = []
    for field in fields:
        value = get_field_value(request, field)
        if value is None or str(value).strip() == "":
            continue
        label = FIELD_LABELS.get(field, field)
        lines.append(f"{label + ':':<18} {value}")
    return "\n".join(lines)


def build_email_body(service_point: str, requests: list, fields: list) -> str:
    count = len(requests)
    noun = "request" if count == 1 else "requests"
    header = f'{count} new “Open – Not yet filled” {noun} for {service_point}.\n'
    blocks = [DIVIDER + "\n" + format_request_block(r, fields) for r in requests]
    return header + "\n" + "\n".join(blocks) + "\n" + DIVIDER


def get_recipients(email_cfg: dict, service_point: str) -> list | None:
    sp_cfg = email_cfg.get("service_points") or {}
    if service_point in sp_cfg:
        recipients = (sp_cfg[service_point] or {}).get("recipients") or []
        if recipients:
            return recipients
    return email_cfg.get("default_recipients") or None


def send_email(email_cfg: dict, recipients: list, subject: str, body: str) -> None:
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = email_cfg["from_address"]
    msg["To"] = ", ".join(recipients)

    host = email_cfg["smtp_host"]
    port = email_cfg.get("smtp_port", 587)
    use_tls = email_cfg.get("use_tls", True)

    with smtplib.SMTP(host, port) as smtp:
        if use_tls:
            smtp.starttls()
        username = email_cfg.get("smtp_username")
        password = email_cfg.get("smtp_password")
        if username and password:
            smtp.login(username, password)
        smtp.sendmail(email_cfg["from_address"], recipients, msg.as_string())


def connect_folio(folio_cfg: dict) -> FolioClient:
    return FolioClient(
        folio_cfg["okapi_url"],
        folio_cfg["tenant"],
        folio_cfg["username"],
        folio_cfg["password"],
    )


def get_new_requests(fc: FolioClient, cfg: dict, last_date: str | None) -> tuple[list, str]:
    query = build_cql_query(last_date)
    limit = cfg.get("request_limit", 1000)
    requests = fetch_new_requests(fc, query, limit)
    if not requests:
        return [], ""
    max_date = max(r["requestDate"] for r in requests)
    return requests, max_date


def notify_service_points(requests: list, cfg: dict) -> bool:
    groups = group_by_service_point(requests)
    email_cfg = cfg["email"]
    request_fields = cfg.get("request_fields") or list(FIELD_LABELS.keys())
    subject_template = email_cfg.get(
        "subject_template",
        "New FOLIO Requests – {service_point} ({count} new request{plural})",
    )

    success = True
    for service_point, group in groups.items():
        recipients = get_recipients(email_cfg, service_point)
        if not recipients:
            log.error(
                "No recipients configured for service point %r and no default_recipients set; skipping",
                service_point,
            )
            success = False
            continue

        count = len(group)
        plural = "" if count == 1 else "s"
        subject = subject_template.format(
            service_point=service_point, count=count, plural=plural
        )
        body = build_email_body(service_point, group, request_fields)

        try:
            send_email(email_cfg, recipients, subject, body)
            log.info(
                "Sent email for %r to %s (%d request(s))",
                service_point,
                recipients,
                count,
            )
        except Exception as exc:
            log.error("Failed to send email for %r: %s", service_point, exc)
            success = False

    return success


def main() -> None:
    cfg = load_config("config.yaml")
    state_file = cfg.get("state_file", "state.json")
    last_date = load_state(state_file)

    if last_date:
        log.info("Resuming from requestDate > %s", last_date)
    else:
        log.info("No state file found; processing all open requests")

    fc = connect_folio(cfg["folio"])
    requests, max_date = get_new_requests(fc, cfg, last_date)

    if not requests:
        log.info("No new requests found")
        return

    log.info("Found %d new request(s)", len(requests))
    if notify_service_points(requests, cfg):
        save_state(state_file, max_date)
        log.info("State updated to requestDate = %s", max_date)
    else:
        log.error("One or more emails failed; state file not updated")


if __name__ == "__main__":
    main()
