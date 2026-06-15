FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    iverilog \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY server.py .

EXPOSE 5000

CMD ["python3", "server.py"]
