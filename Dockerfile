FROM ghcr.io/lehigh-university-libraries/python3.13:main@sha256:86a892c3801acc5a7ec579722a118f64cb2e396115b34be697f90a417878272f

WORKDIR /app

COPY requirements.txt /app
RUN uv pip install \
   --break-system-packages \
   --system \
   -r /app/requirements.txt

COPY . /app

ENV FLASK_APP=application:app
