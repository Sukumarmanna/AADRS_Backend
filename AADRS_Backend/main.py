from fastapi import FastAPI, HTTPException, Request, Body
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import os
import logging
import uvicorn
from typing import Optional

# --- LOGGING SETUP ---
# Isse humein Render ke logs mein pata chalega ki request kab aur kahan fail hui
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AADRS_API")

app = FastAPI(title="AADRS Backend")

# --- IMPROVED CORS SETTINGS ---
# Isse mobile app aur web dono se connection allow hoga
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE CONNECTION ---
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://kumarsanumanna_db_user:Sukumar123456@aadrs-cluster.xgenmea.mongodb.net/aadrs_db?retryWrites=true&w=majority")

try:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.aadrs_db
    users_collection = db.users
    logger.info("✅ SUCCESS: Connected to MongoDB Atlas")
except Exception as e:
    logger.error(f"❌ DATABASE ERROR: {e}")

# --- SCHEMAS ---
class RegisterSchema(BaseModel):
    name: str
    email: str
    mobNo: str
    password: str
    state: str = "Jharkhand"
    locality: str
    pincode: str

class LoginSchema(BaseModel):
    identifier: str  # Mobile number or Email
    password: str

# --- ENDPOINTS ---

@app.get("/")
async def root():
    logger.info("Health check ping received")
    return {"status": "Online", "msg": "AADRS Backend is Live and Secure"}

@app.post("/register")
async def register(data: RegisterSchema):
    try:
        logger.info(f"Registration attempt for: {data.mobNo}")
        
        # 1. Check if user already exists (Mobile or Email)
        existing_user = await users_collection.find_one({
            "$or": [{"mobNo": data.mobNo}, {"email": data.email}]
        })
        
        if existing_user:
            logger.warning(f"Registration failed: User {data.mobNo} already exists")
            return {"status": "error", "message": "Mobile number or Email already registered"}
        
        # 2. Insert new user
        user_data = data.dict()
        result = await users_collection.insert_one(user_data)
        
        logger.info(f"✅ User registered successfully: {data.mobNo}")
        return {
            "status": "success", 
            "message": "Registration successful",
            "user_id": str(result.inserted_id)
        }
        
    except Exception as e:
        logger.error(f"❌ REGISTER ENDPOINT ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error during registration")

@app.post("/login")
async def login(data: LoginSchema):
    try:
        logger.info(f"Login attempt for: {data.identifier}")
        
        # 1. Search user by Email or Mobile
        user = await users_collection.find_one({
            "$or": [{"email": data.identifier}, {"mobNo": data.identifier}],
            "password": data.password
        })
        
        if user:
            logger.info(f"✅ Login successful for: {data.identifier}")
            return {
                "status": "success", 
                "message": "Login successful",
                "mobNo": user["mobNo"],
                "name": user["name"]
            }
        
        logger.warning(f"❌ Login failed: Invalid credentials for {data.identifier}")
        # Send 401 for unauthorized access
        raise HTTPException(status_code=401, detail="Invalid Mobile/Email or Password")
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"❌ LOGIN ENDPOINT ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error during login")

# --- SERVER START ---
if __name__ == "__main__":
    # Render requires dynamic port binding
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
