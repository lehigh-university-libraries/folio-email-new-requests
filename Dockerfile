FROM ghcr.io/lehigh-university-libraries/python3.13:main@sha256:9c947b1deaa1602499df3ab59b5ff0b0f430405fcebe1cab6fb106388fe735d4

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
