FROM ghcr.io/lehigh-university-libraries/python3.13:main@sha256:6073bec11710c284824a17656218e657cc6bce090aa03a8178b352da3e43aeda

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
