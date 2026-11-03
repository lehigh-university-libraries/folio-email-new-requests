FROM ghcr.io/lehigh-university-libraries/python3.13:main@sha256:dd5e5b07fbdfd403b8ff9998af3ef4e0b2b0f23224573171204bc978a69c7fe5

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
