"""
绑定管理 API
为前端 admin 提供绑定管理功能
"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends
import logging
from src.api.deps import verify_token
from src.models.binding import BindingResponse
from src.services.binding_service import BindingService

logger = logging.getLogger(__name__)
binding_router = APIRouter(prefix="/bindings", tags=["Bindings"])


@binding_router.get("", response_model=List[BindingResponse])
async def list_bindings(token_info: dict = Depends(verify_token)):
    """获取所有绑定列表"""
    bindings = BindingService.get_all_bindings()
    return bindings


@binding_router.delete("/{openid}")
async def delete_binding(openid: str, token_info: dict = Depends(verify_token)):
    """删除绑定"""
    success = BindingService.delete_binding(openid)
    if success:
        return {"code": 200, "message": "删除成功"}
    else:
        raise HTTPException(status_code=404, detail="绑定不存在")


@binding_router.get("/{openid}", response_model=BindingResponse)
async def get_binding(openid: str, token_info: dict = Depends(verify_token)):
    """获取指定用户的绑定"""
    binding = BindingService.get_binding_by_openid(openid)
    if binding:
        return binding
    else:
        raise HTTPException(status_code=404, detail="绑定不存在")
