from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Request
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
import shutil
import logging

# Logging setup taaki Render logs mein error saaf dikhe
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 1. Folder setup for Profile Pictures
UPLOAD_DIR = "static/profile_pics"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.error(f"Static mounting error: {e}")

# 2. CORS Policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MONGODB CONNECTION ---
# Render Environment Variable se URL uthayega
MONGO_URL = os.getenv("MONGO_URL")

if not MONGO_URL:
    logger.warning("MONGO_URL not found in environment variables, using fallback!")
    MONGO_URL = "mongodb+srv://kumarsanumanna_db_user:Sukumar123456@aadrs-cluster.xgenmea.mongodb.net/aadrs_db?retryWrites=true&w=majority"

try:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.aadrs_db
    users_collection = db.users
    alerts_collection = db.alerts
    logger.info("Successfully connected to MongoDB Atlas")
except Exception as e:
    logger.error(f"MongoDB Connection Failed: {e}")

# --- MODELS ---
class LoginSchema(BaseModel):
    identifier: str
    password: str

# --- ENDPOINTS ---

@app.get("/")
async def root():
    return {"status": "Online", "msg": "AADRS Backend is Live", "database": "Connected"}

@app.post("/login")
async def login(data: LoginSchema):
    user = await users_collection.find_one({
        "$or": [{"email": data.identifier}, {"mobNo": data.identifier}],
        "password": data.password
    })
    if user:
        return {"message": "Login Success", "mobNo": user["mobNo"]}
    raise HTTPException(status_code=401, detail="Invalid Credentials")

@app.post("/send-alert")
async def send_alert(request: Request):
    try:
        alert_data = await request.json()
        result = await alerts_collection.insert_one(alert_data)
        logger.info(f"Alert Inserted: {result.inserted_id}")
        return {"status": "Success", "id": str(result.inserted_id)}
    except Exception as e:
        logger.error(f"Alert Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid Alert Data")

@app.get("/get-alerts")
async def get_alerts():
    alerts = await alerts_collection.find().sort("_id", -1).to_list(10)
    for a in alerts:
        a["_id"] = str(a["_id"])
    return alerts

@app.get("/profile/{mob_no}")
async def get_profile(mob_no: str):
    user = await users_collection.find_one({"mobNo": mob_no}, {"password": 0, "_id": 0})
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/upload-profile-pic")
async def upload_pic(mobNo: str = Form(...), profilePic: UploadFile = File(...)):
    try:
        file_ext = profilePic.filename.split(".")[-1]
        file_name = f"{mobNo}_profile.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(profilePic.file, buffer)
            
        db_path = f"/static/profile_pics/{file_name}"
        await users_collection.update_one({"mobNo": mobNo}, {"$set": {"profilePic": db_path}})
        return {"message": "Upload Success", "path": db_path}
    except Exception as e:
        logger.error(f"Upload Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
