# Despliegue en Coolify (puerto 8003)

## Qué se ha preparado

- `Dockerfile` — build de la app con gunicorn, escucha en `0.0.0.0:${PORT}` (por defecto `8003`).
- `.dockerignore` — excluye `venv/`, bases de datos locales, uploads, logs y docs del build.

La app detecta sola SQLite vs PostgreSQL según exista o no `DATABASE_URL` (igual que en Render), así que no hace falta tocar código.

---

## Paso 1: Subir los cambios a tu repositorio Git

Coolify despliega desde un repo Git (GitHub/GitLab u otro).

```bash
git add Dockerfile .dockerignore COOLIFY.md
git commit -m "Añadir Dockerfile para despliegue en Coolify"
git push origin master
```

---

## Paso 2: Crear el recurso en Coolify

1. En tu proyecto de Coolify → **New Resource** → **Application**.
2. Fuente: **Public/Private Repository** (o **GitHub App** si ya tienes la integración conectada) → selecciona este repo y la rama `master`.
3. **Build Pack**: `Dockerfile` (Coolify lo detecta automáticamente al ver el `Dockerfile` en la raíz).
4. **Ports Exposes**: `8003`.
5. **Ports Mappings** (si quieres fijar el puerto del host, opcional): `8003:8003`.

---

## Paso 3: Variables de entorno

En la pestaña **Environment Variables** del recurso:

| Variable | Valor | Obligatoria |
|----------|-------|--------------|
| `SECRET_KEY` | genera una clave aleatoria (ver abajo) | Sí |
| `FLASK_ENV` | `production` | Recomendada |
| `PORT` | `8003` | Ya viene por defecto en el Dockerfile, pero puedes fijarla explícita |
| `DATABASE_URL` | URL de Postgres (ver Paso 4) | Solo si usas Postgres |

Generar `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Paso 4: Base de datos — elige una opción

### Opción A: SQLite + volumen persistente (más simple)

Como el contenedor se reconstruye en cada deploy, sin volumen perderías la base de datos y los ficheros subidos.

En **Storages** del recurso, añade dos montajes persistentes:

| Nombre | Ruta en el contenedor |
|--------|------------------------|
| `db` | `/app/admin` |
| `uploads` | `/app/uploads` |

Esto conserva `protectora.db` y las fotos/vídeos/PDFs subidos entre despliegues.

### Opción B: PostgreSQL (recomendado para producción)

1. En Coolify: **New Resource** → **Database** → **PostgreSQL**. Despliega ese servicio en el mismo proyecto.
2. Copia la connection string interna que Coolify genera (algo como `postgresql://user:pass@postgres-service:5432/dbname`).
3. Añádela como variable de entorno `DATABASE_URL` en la app web.
4. Sigue montando el volumen de `uploads` (Paso A) — Postgres solo cubre la base de datos, no los ficheros subidos.

---

## Paso 5: Dominio y HTTPS

1. En **Domains**, añade tu dominio o subdominio (ej. `protectora.tudominio.com`), o usa el subdominio `*.sslip.io` que Coolify asigna automáticamente.
2. Coolify emite el certificado HTTPS (Let's Encrypt) automáticamente si el dominio apunta a tu servidor.
3. Si accedes solo por IP:puerto, la URL será `http://TU_SERVIDOR:8003`.

---

## Paso 6: Deploy

1. Pulsa **Deploy**. Coolify construye la imagen desde el `Dockerfile` y la levanta.
2. Revisa los **Logs** de build y runtime — deberías ver el mensaje de arranque de Flask/gunicorn y el aviso de "Usando SQLite" o "Usando PostgreSQL" según la opción elegida.
3. Cuando el estado sea **Running/Healthy**, entra a la URL asignada.

### URLs una vez desplegado
```
Sitio público: http://TU_DOMINIO_O_IP:8003
Panel admin:   http://TU_DOMINIO_O_IP:8003/admin
```

**Credenciales por defecto:** `admin` / `protectora2026` — cámbialas en `/admin/change-password` nada más entrar.

---

## Actualizar la app tras cambios

```bash
git add .
git commit -m "Descripción del cambio"
git push origin master
```

Si tienes activado el webhook/auto-deploy de Coolify para esta rama, se despliega solo; si no, pulsa **Redeploy** manualmente en el panel.

---

## Troubleshooting

**El contenedor arranca pero no responde en 8003**
Comprueba que `Ports Exposes` = `8003` coincide con el `EXPOSE`/`PORT` del Dockerfile, y que el proxy de Coolify apunta a ese puerto.

**Se pierden las fotos subidas o la base de datos tras cada deploy**
Falta el volumen persistente del Paso 4 — sin él, cada build parte de una imagen limpia.

**Error `psycopg2` / build falla instalando dependencias**
El Dockerfile ya incluye `gcc`, `libpq-dev`, `libjpeg-dev`, `zlib1g-dev` para compilar Pillow/psycopg2 si no hay wheel precompilada para la arquitectura del servidor.

**Cambios de código no se reflejan**
Verifica que el deploy realmente reconstruyó la imagen (no quedó cacheada) y, si tocaste JS, sube la versión `?v=N` en los `<script>` como indica el CLAUDE.md del proyecto para evitar caché del navegador.
