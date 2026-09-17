from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models
from database import engine
from api import router as api_router

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NEXUS Core API",
    description="Central API Node for the NEXUS Personal Digital Infrastructure",
    version="0.1.0"
)

# Allow cross-origin requests from any client for MVP
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "nexus-core"}

# Include the API router
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
