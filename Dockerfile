FROM ghcr.io/lehigh-university-libraries/python3.13:main@sha256:310b999ea1fc7c58cd2da9ca8290602ccfa30e06e6d605a4cfd0fdd17c4f5490

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
