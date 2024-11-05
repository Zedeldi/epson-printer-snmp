# syntax=docker/dockerfile:1

FROM python:3-alpine

WORKDIR /usr/src/app
COPY main.py models.json requirements.txt .

RUN apk add --no-cache build-base net-snmp net-snmp-dev
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "main.py"]
