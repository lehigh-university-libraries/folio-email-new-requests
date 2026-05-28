FROM ghcr.io/lehigh-university-libraries/python3.13:main@sha256:1a061509da7a8b739f387e7500e164d53316424c7ec3f464e3eed7d3fc9fcd8b

WORKDIR /app

COPY requirements.txt /app
RUN uv pip install \
   --break-system-packages \
   --system \
   -r /app/requirements.txt

COPY . /app

ENV FLASK_APP=application:app \
    HOME=/tmp \
    PORT=5000
