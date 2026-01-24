"""
腾讯云 COS 服务模块
"""
import logging
import os
from typing import Optional

from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client

logger = logging.getLogger(__name__)

# COS 配置
COS_SECRET_ID = os.getenv("COS_SECRET_ID", "")
COS_SECRET_KEY = os.getenv("COS_SECRET_KEY", "")
COS_REGION = os.getenv("COS_REGION", "ap-shanghai")
COS_BUCKET = os.getenv("COS_BUCKET", "")
COS_BASE_URL = os.getenv("COS_BASE_URL", "")
COS_ROOT_DIR = os.getenv("COS_ROOT_DIR", "")

_cos_client = None


def init_cos() -> Optional[CosS3Client]:
    """初始化 COS 客户端"""
    global _cos_client

    if not all([COS_SECRET_ID, COS_SECRET_KEY, COS_REGION, COS_BUCKET]):
        logger.warning("[COS] 配置不完整，跳过初始化")
        return None

    try:
        config = CosConfig(
            Region=COS_REGION,
            SecretId=COS_SECRET_ID,
            SecretKey=COS_SECRET_KEY,
        )
        _cos_client = CosS3Client(config)
        logger.info(f"[COS] 初始化成功: bucket={COS_BUCKET}, region={COS_REGION}")
        return _cos_client
    except Exception as e:
        logger.error(f"[COS] 初始化失败: {e}")
        return None


def get_cos_url(filename: str) -> str:
    """获取文件的 COS 访问 URL"""
    if COS_BASE_URL:
        base = COS_BASE_URL.rstrip("/")
        if COS_ROOT_DIR:
            return f"{base}/{COS_ROOT_DIR}/{filename}"
        return f"{base}/{filename}"
    else:
        # 使用默认的 COS URL 格式
        return f"https://{COS_BUCKET}.cos.{COS_REGION}.myqcloud.com/{COS_ROOT_DIR}/{filename}"


def upload_file(local_path: str) -> Optional[str]:
    """
    上传文件到 COS

    Args:
        local_path: 本地文件路径

    Returns:
        COS 访问 URL，失败返回 None
    """
    if not _cos_client:
        if not init_cos():
            return None

    if not os.path.exists(local_path):
        logger.error(f"[COS] 文件不存在: {local_path}")
        return None

    filename = os.path.basename(local_path)
    cos_key = f"{COS_ROOT_DIR}/{filename}" if COS_ROOT_DIR else filename

    try:
        logger.info(f"[COS] 开始上传: {local_path} -> {cos_key}")

        _cos_client.upload_file(
            Bucket=COS_BUCKET,
            Key=cos_key,
            LocalFilePath=local_path
        )

        url = get_cos_url(filename)
        logger.info(f"[COS] 上传成功: {url}")
        return url

    except Exception as e:
        logger.error(f"[COS] 上传失败: {e}")
        return None


def upload_image(local_path: str) -> Optional[str]:
    """
    上传图片到 COS

    Args:
        local_path: 本地图片路径

    Returns:
        COS 访问 URL，失败返回 None
    """
    return upload_file(local_path)
