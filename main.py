import sys
print("RUNNING PYTHON:", sys.executable)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from auth.auth_router import router as auth_router

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# -----------------------------
# ✅ Corrected CORS Configuration
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://ukari-frontend.vercel.app",  # for future deployment
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/auth", tags=["Auth"])

@app.get("/")
def root():
    return {"message": "U-KARI backend running"}
