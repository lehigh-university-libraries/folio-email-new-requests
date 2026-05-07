FROM ghcr.io/lehigh-university-libraries/python3.13:main@sha256:0da80da2cfd2869bf94cfa2327641300d2a3c97fe3922946b18f4454045bb71f

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
