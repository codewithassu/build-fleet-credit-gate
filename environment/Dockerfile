FROM python:3.13-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pytest==8.4.1

COPY repo/ /app/

RUN mkdir -p /app/output \
    && chmod +x /app/src/gate.py /app/data/smoke/run_smoke.py

# Do not COPY solution/ or tests/ — mounted at verification time.
