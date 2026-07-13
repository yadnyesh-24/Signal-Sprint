import os
import shutil
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from predict import load_model, predict

ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading model...")
    ml_models["model"] = load_model()
    print("Model loaded successfully")
    yield
    ml_models.clear()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/predict")
async def process_image(file: UploadFile = File(...)):
    temp_file_path = f"temp_{file.filename}"
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        result = predict(ml_models["model"], temp_file_path)
        
        if result == 1:
            message = "DMC Action Required"
            action_required = True
        else:
            message = "No Action Required"
            action_required = False
            
        return {"result": result, "message": message, "action_required": action_required}
        
    finally:
            os.remove(temp_file_path)


class NotifyPayload(BaseModel):
    lat: float
    lng: float
    accuracy: float | None = None
    label: int | None = None
    timestamp: str | None = None

@app.post("/notify")
async def notify_location(payload: NotifyPayload):
    return {
        "ok": True,
        "received": {
            "lat": payload.lat,
            "lng": payload.lng,
            "accuracy": payload.accuracy,
            "label": payload.label,
            "timestamp": payload.timestamp,
        },
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
