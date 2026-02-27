FROM python:3.11-slim
RUN apt-get update && apt-get install -y traceroute iputils-ping dnsutils && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY routerunner.py /app/routerunner.py
CMD ["python", "-u", "/app/routerunner.py"]
