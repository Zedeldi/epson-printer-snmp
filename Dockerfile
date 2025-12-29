# syntax=docker/dockerfile:1

FROM python:3-slim

WORKDIR /usr/src/app
COPY main.py models.json requirements.txt .

# dependencies for easysnmp
RUN apt-get update && apt-get install -y \
	gcc \
	libsnmp-dev \
	snmp \
	&& rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "main.py"]
