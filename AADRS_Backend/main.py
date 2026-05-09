from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Request
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
import shutil

app = FastAPI()

# 1. Folder setup for Profile Pictures
UPLOAD_DIR = "static/profile_pics"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 2. Majboot CORS Policy (Mobile App requests ke liye zaroori)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MONGODB CONNECTION ---
MONGO_URL = "mongodb+srv://kumarsanumanna_db_user:Sukumar123456@aadrs-cluster.xgenmea.mongodb.net/aadrs_db?retryWrites=true&w=majority"
client = AsyncIOMotorClient(MONGO_URL)
db = client.aadrs_db
users_collection = db.users
alerts_collection = db.alerts

# --- MODELS FOR VALIDATION ---
class LoginSchema(BaseModel):
    identifier: str
    password: str

# --- ENDPOINTS ---

@app.get("/")
async def root():
    return {"status": "Online", "msg": "AADARS Backend is Running"}

# LOGIN (Updated with Print statements for Debugging)
@app.post("/login")
async def login(data: LoginSchema):
    print(f"📩 Login Attempt: {data.identifier}") # Terminal mein dikhega
    user = await users_collection.find_one({
        "$or": [{"email": data.identifier}, {"mobNo": data.identifier}],
        "password": data.password
    })
    
    if user:
        print(f"✅ Login Success: {data.identifier}")
        return {"message": "Login Success", "mobNo": user["mobNo"]}
    
    print(f"❌ Login Failed: {data.identifier}")
    raise HTTPException(status_code=401, detail="Invalid Credentials")

# SEND ALERT (App to Dashboard)
@app.post("/send-alert")
async def send_alert(request: Request):
    try:
        alert_data = await request.json()
        result = await alerts_collection.insert_one(alert_data)
        print(f"🚨 ALERT RECEIVED: User {alert_data.get('mobNo')}")
        return {"status": "Success", "id": str(result.inserted_id)}
    except Exception as e:
        print(f"🔥 Alert Error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid Alert Data")

# GET ALERTS (For Web Dashboard)
@app.get("/get-alerts")
async def get_alerts():
    alerts = await alerts_collection.find().sort("_id", -1).to_list(10)
    for a in alerts:
        a["_id"] = str(a["_id"])
    return alerts

# PROFILE FETCH
@app.get("/profile/{mob_no}")
async def get_profile(mob_no: str):
    user = await users_collection.find_one({"mobNo": mob_no}, {"password": 0, "_id": 0})
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not found")

# IMAGE UPLOAD
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
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # 0.0.0.0 means it will accept requests from your Mobile IP
    uvicorn.run(app, host="0.0.0.0", port=8000)