# Dockerfile per ice-pulse-api
FROM python:3.13-alpine	

# Metadata
LABEL maintainer="ice-pulse-team"
LABEL description="Ice Pulse API Backend"
LABEL version="0.0.4"

# Variabili di ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=80
ENV ENVIRONMENT=production

# Installa dipendenze di sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crea utente non-root per sicurezza
RUN groupadd -r appuser && useradd -r -g appuser appuser

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