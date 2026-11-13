FROM ghcr.io/lehigh-university-libraries/python3.13:main@sha256:70b1c5653bc9712551f4de89a5fc24fd504901528c80651ef127627d26567093

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
