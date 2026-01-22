from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

telegram_router = APIRouter(prefix="/telegram", tags=["Telegram"])

# Webhook functionality has been disabled.
# This router is currently empty but kept for potential future HTTP API extensions.
