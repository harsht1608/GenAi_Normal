# --- Stage 1: builder (install deps) ---
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# system deps for some packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libsasl2-dev \
    && rm -rf /var/lib/apt/lists/*

# copy and install requirements
COPY backend/requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

# --- Stage 2: runtime image ---
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/srv/app

# create non-root user
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR $APP_HOME

# copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# copy app code
COPY backend/ $APP_HOME/

# logs dir
RUN mkdir -p /var/log/gemini-backend && chown -R appuser:appuser /var/log/gemini-backend

# files permissions
RUN chown -R appuser:appuser $APP_HOME

USER appuser

ENV PATH="$APP_HOME:$PATH"

# port
EXPOSE 8000

# Use gunicorn with uvicorn workers — tuned for small machines, tune workers for your CPU
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "120", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]

# quick healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
