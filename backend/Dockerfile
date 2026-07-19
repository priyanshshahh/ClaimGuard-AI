FROM python:3.12-slim

WORKDIR /app

# system deps kept minimal; xgboost needs libgomp
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-serve.txt .
RUN pip install --no-cache-dir -r requirements-serve.txt

COPY . .

# trained artifacts ship with the repo in models/; data/ is created at runtime
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Render injects $PORT; default 8000 for local docker run
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import os,urllib.request; p=os.environ.get('PORT','8000'); urllib.request.urlopen(f'http://localhost:{p}/health')" || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
