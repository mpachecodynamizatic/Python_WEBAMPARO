FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema para compilar Pillow/psycopg2 si no hay wheel precompilada
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads/fotos uploads/videos uploads/pdfs

ENV PORT=8003
EXPOSE 8003

CMD ["sh", "-c", "gunicorn --chdir admin app:app --bind 0.0.0.0:${PORT} --workers 2"]
