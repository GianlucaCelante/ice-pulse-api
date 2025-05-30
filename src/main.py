# main.py - Basic FastAPI app per ice-pulse-api
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
import uvicorn

# Configurazione app
app = FastAPI(
    title="Ice Pulse API",
    description="Backend API for Ice Pulse IoT HACCP System",
    version=os.getenv("VERSION", "0.0.4"),
)

# Health check endpoint (necessario per Docker health check)
@app.get("/health")
async def health_check():
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "version": os.getenv("VERSION", "0.0.4"),
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    )

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Ice Pulse API is running",
        "version": os.getenv("VERSION", "0.0.4"),
        "environment": os.getenv("ENVIRONMENT", "development")
    }

# API endpoints (aggiungi qui i tuoi endpoint esistenti)
@app.get("/api/v1/status")
async def api_status():
    return {
        "api": "ice-pulse",
        "status": "operational",
        "timestamp": "2024-01-01T00:00:00Z"  # Sostituisci con datetime reale
    }

# Entry point per development
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 80)),
        reload=os.getenv("ENVIRONMENT") == "development"
    )