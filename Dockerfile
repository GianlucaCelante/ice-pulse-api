# Dockerfile per ice-pulse-api
FROM python:3.9-alpine

# Metadata
LABEL maintainer="ice-pulse-team"
LABEL description="Ice Pulse API Backend"

# Variabili di ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=80
ENV ENVIRONMENT=production

# Installa dipendenze di sistema (Alpine usa apk invece di apt-get)
RUN apk add --no-cache \
    curl \
    gcc \
    musl-dev \
    postgresql-dev

# Crea utente non-root per sicurezza
RUN addgroup -g 1000 appuser && \
    adduser -D -s /bin/sh -u 1000 -G appuser appuser

# Crea directory di lavoro
WORKDIR /app

# Copia requirements prima del codice (per cache Docker layers)
COPY requirements.txt .

# Installa dipendenze Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia il codice dell'applicazione
COPY . .

# Cambia ownership dei file all'utente appuser
RUN chown -R appuser:appuser /app

# Cambia all'utente non-root
USER appuser

# Esponi la porta
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:$PORT/health || exit 1

# Comando di avvio
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]