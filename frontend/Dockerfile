# --- Stage 1: builder ---
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

COPY frontend/requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

# --- Stage 2: runtime ---
FROM python:3.11-slim

ENV APP_HOME=/srv/frontend
WORKDIR $APP_HOME

# non-root user
RUN useradd --create-home --shell /bin/bash appuser
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY frontend/ $APP_HOME/

RUN chown -R appuser:appuser $APP_HOME
USER appuser

EXPOSE 8501

# Streamlit production-friendly flags
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ENABLECORS=false \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

CMD ["streamlit", "run", "streamlit_app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
