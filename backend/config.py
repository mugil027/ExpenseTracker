import os
from datetime import timedelta

class Config:
    # Use MongoDB Atlas URI or local
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/expense_tracker")

    # JWT / Auth
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)

    # CORS (adjust for your frontend origin)
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")