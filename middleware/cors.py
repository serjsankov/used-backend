from fastapi.middleware.cors import CORSMiddleware
from config import FRONTEND_URLS

def add_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=FRONTEND_URLS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )