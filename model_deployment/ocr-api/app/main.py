import os, io, json
from datetime import datetime
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
from receipt_extractor import extract_from_bytes
import uvicorn

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/extract")
async def extract(file: UploadFile = File(...), save_to_db: bool = False, db_type: str = "firestore", background: bool = False, background_tasks: BackgroundTasks = None):
    try:
        img_bytes = await file.read()
        items = extract_from_bytes(img_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse({"status":"ok", "items": items})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
