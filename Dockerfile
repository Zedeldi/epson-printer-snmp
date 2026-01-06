# syntax=docker/dockerfile:1
FROM python:3-slim

WORKDIR /usr/src/app
# dependencies for easysnmp
RUN apt-get update && apt-get install --no-install-recommends --assume-yes \
    gcc \
    libsnmp-dev \
    snmp \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py models.json .

ENTRYPOINT ["python", "main.py"]
