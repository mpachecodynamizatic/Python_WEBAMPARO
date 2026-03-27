# Dockerfile para Protectora Burjassot
FROM python:3.11-slim

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY admin/requirements.txt requirements.txt

# Instalar dependencias Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn psycopg2-binary

# Copiar código
COPY . .

# Crear directorios necesarios
RUN mkdir -p uploads/fotos uploads/videos uploads/pdfs

# Exponer puerto
EXPOSE 5000

# Script de inicio
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--chdir", "admin", "app:app"]
