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
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# --- DATABASE CONNECTION ---
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://kumarsanumanna_db_user:Sukumar123456@aadrs-cluster.xgenmea.mongodb.net/aadrs_db?retryWrites=true&w=majority")

try:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.aadrs_db
    users_collection = db.users
    logger.info("✅ Connected to MongoDB Atlas")
except Exception as e:
    logger.error(f"❌ MongoDB Connection Error: {e}")

# --- SCHEMAS ---
class RegisterSchema(BaseModel):
    name: str
    email: str
    mobNo: str
    password: str
    state: str = "Jharkhand"
    locality: str
    pincode: str

# --- ENDPOINTS ---

@app.get("/")
async def root():
    return {"status": "Online", "msg": "AADRS Backend is Live"}

@app.post("/register")
async def register(data: RegisterSchema):
    try:
        # Check if user already exists
        existing_user = await users_collection.find_one({"mobNo": data.mobNo})
        if existing_user:
            return {"status": "error", "message": "Mobile number already registered"}
        
        user_dict = data.dict()
        result = await users_collection.insert_one(user_dict)
        logger.info(f"👤 New User Registered: {data.mobNo}")
        return {"status": "success", "message": "Account created successfully", "id": str(result.inserted_id)}
    
    except Exception as e:
        logger.error(f"❌ Registration Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Render needs this port binding
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
