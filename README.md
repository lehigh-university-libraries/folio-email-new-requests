# folio-email-new-requests

Polls FOLIO for new "Open – Not yet filled" circulation requests and emails
configured staff lists, grouped by pickup service point. 

Runs either as a
CLI script (invoked directly or via cron) or as a persistent HTTP server
(via Docker) that can be triggered by cron or on demand by a discovery layer.

## Email format

```
Subject: New FOLIO Requests – Linderman (3 new requests)

3 new "Open – Not yet filled" requests for Linderman.

──────────────────────────────────────────────
Request Date:      2026-04-30T14:23:11.000+00:00
Patron Barcode:    12345678
Item Barcode:      39151008775948
Title:             Burning for the Buddha
Call Number:       294.343 B469b
Request Type:      Page
Comments:          Please hold at front desk
──────────────────────────────────────────────
Request Date:      2026-04-30T15:01:44.000+00:00
Patron Barcode:    98765432
Item Barcode:      39151008776111
Title:             Introduction to Library Science
Call Number:       Z665 .I58
Request Type:      Hold
──────────────────────────────────────────────
```

One email is sent per service point that has new requests. If a service point
has no new requests, no email is sent for it.

## Requirements

- Python 3.10+
- FOLIO APIs
- An SMTP server

## Installation

```
pip install -r requirements.txt
```

## Configuration

Copy `config.yaml.example` to `config.yaml` and fill in your values before the first run.

### FOLIO connection

```yaml
folio:
  okapi_url: https://your-folio-api.example.com
  tenant: your_tenant
  username: admin
  password: secret
```

The FOLIO user must have the **Requests: View** permission.

### Email

```yaml
email:
  smtp_host: smtp.example.com
  smtp_port: 587
  use_tls: true
  smtp_username: sender@example.com
  smtp_password: secret
  from_address: folio-requests@example.com
  subject_template: "New FOLIO Requests – {service_point} ({count} new request{plural})"
```

The `subject_template` supports three placeholders: `{service_point}`,
`{count}`, and `{plural}` (empty string for 1, `s` otherwise).

### Recipient lists

Keys under `service_points` must match the `pickupServicePoint.name`
value returned by FOLIO exactly (check a live request record if unsure).

```yaml
email:
  service_points:
    "Linderman":
      recipients:
        - staff1@example.com
        - staff2@example.com
    "Fairchild-Martindale":
      recipients:
        - staff3@example.com

  default_recipients:
    - fallback@example.com
```

If a service point is not listed under `service_points`, the script falls back
to `default_recipients`. If neither is configured for a given service point,
the script logs an error and skips that group.

### Request fields

Controls which fields appear in each email block and in what order. Values are
camelCase dot-paths matching the FOLIO JSON response.

```yaml
request_fields:
  - requestDate
  - requester.barcode
  - item.barcode
  - instance.title
  - item.callNumber
  - requestType
  - patronComments
```

Available fields:

| Config value | Description |
|---|---|
| `requestDate` | Date and time the request was placed |
| `requester.barcode` | Patron barcode |
| `item.barcode` | Item barcode |
| `instance.title` | Title of the requested instance |
| `item.callNumber` | Call number |
| `requestType` | Hold, Page, or Recall |
| `patronComments` | Patron-supplied comments (omitted from email when empty) |

### Other settings

```yaml
state_file: state.json      # path to the run-state file (auto-created)
request_limit: 1000         # FOLIO API pagination batch size
```

## Usage

The script supports two deployment modes. Both track state the same way:

**First run** — no `state.json` exists yet. The script processes every
currently open "Not yet filled" request, sends emails, then writes `state.json`
with the most recent `requestDate` seen.

**Subsequent runs** — the script queries only for requests newer than the saved
`requestDate`, so each request is emailed exactly once.

To reset and reprocess everything, delete `state.json`.

### CLI mode

```
python new_requests.py
```

Runs the check once and exits.

Schedule with cron to run every 15 minutes:

```
*/15 * * * * cd /path/to/folio-email-new-requests && python new_requests.py >> /var/log/folio-new-requests.log 2>&1
```

The script logs to stdout/stderr with timestamps and exits with a non-zero code
on failure, which cron-monitoring tools can detect.

### Server mode

The Docker image runs a persistent gunicorn HTTP server. Send an empty
`POST /check-requests` to trigger the same check-and-email cycle:

```
curl -X POST http://127.0.0.1:5000/check-requests
```

| Status | Body | Meaning |
|--------|------|---------|
| 200 | `{"found": N}` | Check completed; N new requests processed |
| 409 | `{"error": "check already in progress"}` | Previous check still running |
| 500 | `{"error": "..."}` | FOLIO or email failure |

If a check is already running when a second request arrives, the server returns
`409` immediately rather than queuing a concurrent check that would race on
`state.json`.

**Cron** — schedule the endpoint call instead of the script:

```
*/15 * * * * curl -sf -X POST http://127.0.0.1:5000/check-requests
```

**On-demand** — a discovery layer or ILS integration can POST to the endpoint
immediately after a patron submits a request, triggering a check without waiting
for the next cron interval.

## Docker

1. Clone this repo.
2. Copy `config.yaml.example` to `config.yaml` and fill in your values.
3. Start the server (on Git Bash for Windows, prefix the `docker run` command with `MSYS_NO_PATHCONV=1`):

```
git clone https://github.com/lehigh-university-libraries/folio-email-new-requests
cd folio-email-new-requests
# cp config.yaml.example config.yaml
# edit config.yaml
docker run \
  -v ./:/app \
  -p 5000:5000 \
  --rm \
  --name folio-email-new-requests \
  ghcr.io/lehigh-university-libraries/folio-email-new-requests:main
```

## State file

`state.json` is written automatically and should not be committed to version
control. It contains a single value:

```json
{"last_request_date": "2026-04-30T15:01:44.000+00:00"}
```
