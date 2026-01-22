"""
腾讯云对象存储 COS 服务模块

提供文件上传到 COS 的功能
"""
import os
import logging
from typing import Optional
from qcloud_cos import CosConfig, CosS3Client

logger = logging.getLogger(__name__)

# COS 配置 (从环境变量读取)
COS_SECRET_ID = os.getenv("COS_SECRET_ID", "")
COS_SECRET_KEY = os.getenv("COS_SECRET_KEY", "")
COS_REGION = os.getenv("COS_REGION", "ap-shanghai")
COS_BUCKET = os.getenv("COS_BUCKET", "wecom-1373472507")
COS_BASE_URL = os.getenv("COS_BASE_URL", "https://wecom-1373472507.cos.ap-shanghai.myqcloud.com")

# 存储桶根目录
COS_ROOT_DIR = os.getenv("COS_ROOT_DIR", "lhcos-data")

# 全局 COS 客户端
_cos_client = None


def get_cos_client() -> Optional[CosS3Client]:
    """
    获取 COS 客户端单例

    Returns:
        CosS3Client 实例或 None（如果未配置）
    """
    global _cos_client

    if _cos_client is not None:
        return _cos_client

    # 检查是否配置了必要的环境变量
    if not COS_SECRET_ID or not COS_SECRET_KEY:
        logger.warning("[COS] 未配置 COS_SECRET_ID 或 COS_SECRET_KEY，COS 服务不可用")
        return None

    try:
        config = CosConfig(
            Region=COS_REGION,
            SecretId=COS_SECRET_ID,
            SecretKey=COS_SECRET_KEY,
        )
        _cos_client = CosS3Client(config)
        logger.info(f"[COS] 客户端初始化成功: region={COS_REGION}, bucket={COS_BUCKET}")
        return _cos_client
    except Exception as e:
        logger.error(f"[COS] 客户端初始化失败: {e}")
        return None


def upload_file(
    local_path: str,
    cos_key: Optional[str] = None,
    bucket: str = COS_BUCKET
) -> Optional[str]:
    """
    上传本地文件到 COS

    Args:
        local_path: 本地文件路径
        cos_key: COS 上的对象键，如果为 None 则使用文件名
        bucket: 存储桶名称

    Returns:
        文件的 COS 公网 URL，失败返回 None
    """
    if not os.path.exists(local_path):
        logger.error(f"[COS] 本地文件不存在: {local_path}")
        return None

    client = get_cos_client()
    if not client:
        logger.warning("[COS] 客户端不可用，跳过上传")
        return None

    # 生成 cos_key
    if cos_key is None:
        cos_key = os.path.basename(local_path)

    # 添加根目录
    full_cos_key = f"{COS_ROOT_DIR}/{cos_key}"

    try:
        logger.info(f"[COS] 开始上传: {local_path} -> {bucket}/{full_cos_key}")

        response = client.upload_file(
            Bucket=bucket,
            Key=full_cos_key,
            LocalFilePath=local_path,
        )

        # 上传成功，返回公网 URL
        etag = response.get('ETag', '')
        logger.info(f"[COS] 上传成功: {full_cos_key}, etag={etag[:20]}...")

        # 返回公网 URL
        public_url = f"{COS_BASE_URL}/{full_cos_key}"
        return public_url

    except Exception as e:
        logger.error(f"[COS] 上传失败: {local_path} -> {full_cos_key}, error={e}")
        return None


def upload_fileobj(
    file_data: bytes,
    cos_key: str,
    bucket: str = COS_BUCKET
) -> Optional[str]:
    """
    直接上传字节数据到 COS

    Args:
        file_data: 文件字节数据
        cos_key: COS 上的对象键
        bucket: 存储桶名称

    Returns:
        文件的 COS 公网 URL，失败返回 None
    """
    client = get_cos_client()
    if not client:
        logger.warning("[COS] 客户端不可用，跳过上传")
        return None

    full_cos_key = f"{COS_ROOT_DIR}/{cos_key}"

    try:
        logger.info(f"[COS] 开始上传字节数据: {len(file_data)} bytes -> {bucket}/{full_cos_key}")

        response = client.put_object(
            Bucket=bucket,
            Body=file_data,
            Key=full_cos_key,
            ContentType='application/octet-stream'
        )

        logger.info(f"[COS] 上传成功: {full_cos_key}, etag={response.get('ETag', '')[:20]}...")

        # 返回公网 URL
        public_url = f"{COS_BASE_URL}/{full_cos_key}"
        return public_url

    except Exception as e:
        logger.error(f"[COS] 上传失败: {full_cos_key}, error={e}")
        return None


def delete_file(cos_key: str, bucket: str = COS_BUCKET) -> bool:
    """
    从 COS 删除文件

    Args:
        cos_key: COS 上的对象键
        bucket: 存储桶名称

    Returns:
        是否删除成功
    """
    client = get_cos_client()
    if not client:
        logger.warning("[COS] 客户端不可用，跳过删除")
        return False

    full_cos_key = f"{COS_ROOT_DIR}/{cos_key}"

    try:
        response = client.delete_object(
            Bucket=bucket,
            Key=full_cos_key
        )
        logger.info(f"[COS] 删除成功: {full_cos_key}")
        return True
    except Exception as e:
        logger.error(f"[COS] 删除失败: {full_cos_key}, error={e}")
        return False
