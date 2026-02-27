FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl gnupg && \
    curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | bash && \
    apt-get install -y speedtest && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY speedrunner.py /app/speedrunner.py

CMD ["python", "-u", "/app/speedrunner.py"]
