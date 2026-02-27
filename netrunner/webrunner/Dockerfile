FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY webrunner.py /app/webrunner.py
COPY config.json /app/config.json

ENV CONFIG_FILE=/app/config.json
ENV DATA_DIR=/data

VOLUME ["/data"]

CMD ["python", "/app/webrunner.py"]
