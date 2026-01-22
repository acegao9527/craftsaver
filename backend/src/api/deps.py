from typing import Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

ACCESS_TOKENS: Dict[str, Dict[str, Any]] = {}  # token -> {username, expires_at}

# 测试 token（7天有效）
TEST_TOKEN = "test_token_123456"
ACCESS_TOKENS[TEST_TOKEN] = {
    "username": "test",
    "expires_at": datetime.now() + timedelta(days=7)
}

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """验证 token"""
    token = credentials.credentials
    if token not in ACCESS_TOKENS:
        raise HTTPException(status_code=401, detail="无效的 token")
    token_info = ACCESS_TOKENS[token]
    if datetime.now() > token_info["expires_at"]:
        del ACCESS_TOKENS[token]
        raise HTTPException(status_code=401, detail="token 已过期")
    return token_info
