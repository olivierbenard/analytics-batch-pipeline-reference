FROM python:3.11-slim

WORKDIR /usr/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl build-essential git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt