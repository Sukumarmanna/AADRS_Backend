from fastapi import FastAPI, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging
import uvicorn

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- FIXED CORS SETTINGS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE CONNECTION ---
# Render environment variable use karega, nahi toh fallback connection string
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://kumarsanumanna_db_user:Sukumar123456@aadrs-cluster.xgenmea.mongodb.net/aadrs_db?retryWrites=true&w=majority")

try:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.aadrs_db
    users_collection = db.users
    logger.info("✅ MongoDB Connected")
except Exception as e:
    logger.error(f"❌ MongoDB Error: {e}")

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
    identifier: str
    password: str

# --- ENDPOINTS ---
@app.get("/")
async def root():
    return {"status": "Online", "msg": "AADRS Backend is Live"}

@app.post("/register")
async def register(data: RegisterSchema):
    existing = await users_collection.find_one({"mobNo": data.mobNo})
    if existing:
        return {"status": "error", "message": "Already registered"}
    await users_collection.insert_one(data.dict())
    return {"status": "success", "message": "Registered"}

@app.post("/login")
async def login(data: LoginSchema):
    user = await users_collection.find_one({
        "$or": [{"email": data.identifier}, {"mobNo": data.identifier}],
        "password": data.password
    })
    if user:
        return {"status": "success", "mobNo": user["mobNo"]}
    raise HTTPException(status_code=401, detail="Invalid credentials")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
