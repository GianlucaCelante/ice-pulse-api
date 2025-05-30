# main.py - Ice Pulse API
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
from datetime import datetime

# Configurazione app
app = FastAPI(
    title="Ice Pulse API",
    description="Backend API for Ice Pulse IoT HACCP System",
    version=os.getenv("VERSION", "0.0.7"),
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione, specifica i domini esatti
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint (necessario per Docker health check)
@app.get("/health")
async def health_check():
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "version": os.getenv("VERSION", "0.0.7"),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "🧊 Ice Pulse API is running!",
        "version": os.getenv("VERSION", "0.0.7"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

# API v1 endpoints
@app.get("/api/v1/status")
async def api_status():
    return {
        "api": "ice-pulse",
        "status": "operational",
        "version": os.getenv("VERSION", "0.0.7"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "features": [
            "health-monitoring",
            "temperature-tracking", 
            "alert-system",
            "data-logging"
        ]
    }

# Placeholder endpoints per funzionalità IoT HACCP
@app.get("/api/v1/sensors")
async def get_sensors():
    return {
        "sensors": [
            {
                "id": "temp_001",
                "type": "temperature",
                "location": "freezer_1",
                "status": "active",
                "last_reading": -18.5,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            {
                "id": "temp_002", 
                "type": "temperature",
                "location": "fridge_1",
                "status": "active",
                "last_reading": 4.2,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        ]
    }

@app.get("/api/v1/alerts")
async def get_alerts():
    return {
        "alerts": [],
        "count": 0,
        "last_check": datetime.utcnow().isoformat() + "Z"
    }

# Entry point per development locale
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 80)),
        reload=os.getenv("ENVIRONMENT") == "development"
    )