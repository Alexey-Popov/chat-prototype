"""API routers"""
from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(chat_router, prefix="/api/chat", tags=["chat"])

__all__ = ["api_router"]
