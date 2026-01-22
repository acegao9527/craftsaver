"""
消息管理 API
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
message_router = APIRouter(prefix="/message", tags=["Message"])

from src.api.deps import verify_token


@message_router.get("/list")
async def list_messages(
    page: int = 1,
    size: int = 10,
    source: Optional[str] = None,
    keyword: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    token_info: dict = Depends(verify_token)
):
    """获取消息列表"""
    try:
        from src.services.database import DatabaseService
        conn = DatabaseService.get_connection()
        cursor = conn.cursor()

        # 构建查询条件
        conditions = ["1=1"]
        params = []
        if source:
            conditions.append("source = ?")
            params.append(source)
        if keyword:
            conditions.append("(content LIKE ? OR from_user LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if start_date:
            conditions.append("DATE(created_at) >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(created_at) <= ?")
            params.append(end_date)

        where = " AND ".join(conditions)
        offset = (page - 1) * size

        # 查询总数
        cursor.execute(f"SELECT COUNT(*) FROM unified_messages WHERE {where}", params)
        total = cursor.fetchone()[0]

        # 查询列表
        query = f"""
            SELECT id, source, from_user, from_user as sender_name, 
                   '' as receiver_id, '' as receiver_name,
                   content, msg_type, created_at
            FROM unified_messages
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([size, offset])
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "source": row[1],
                "sender_id": row[2],
                "sender_name": row[3],
                "receiver_id": row[4],
                "receiver_name": row[5],
                "content": row[6],
                "msg_type": row[7],
                "created_at": row[8]
            })

        return {"code": 200, "data": {"list": data, "total": total}}
    except Exception as e:
        logger.error(f"[Admin] 获取消息列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@message_router.get("/{msg_id}")
async def get_message(msg_id: int, token_info: dict = Depends(verify_token)):
    """获取消息详情"""
    try:
        from src.services.database import DatabaseService
        conn = DatabaseService.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, source, from_user, from_user as sender_name, 
                   '' as receiver_id, '' as receiver_name,
                   content, msg_type, raw_data, created_at
            FROM unified_messages WHERE id = ?
        """, (msg_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="消息不存在")

        data = {
            "id": row[0],
            "source": row[1],
            "sender_id": row[2],
            "sender_name": row[3],
            "receiver_id": row[4],
            "receiver_name": row[5],
            "content": row[6],
            "msg_type": row[7],
            "raw_data": row[8],
            "created_at": row[9]
        }

        return {"code": 200, "data": data}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"[Admin] 获取消息详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@message_router.delete("/{msg_id}")
async def delete_message(msg_id: int, token_info: dict = Depends(verify_token)):
    """删除消息"""
    try:
        from src.services.database import DatabaseService
        conn = DatabaseService.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM unified_messages WHERE id = ?", (msg_id,))
        conn.commit()
        conn.close()

        logger.info(f"[Admin] 删除消息 ID: {msg_id}")
        return {"code": 200, "message": "删除成功"}
    except Exception as e:
        logger.error(f"[Admin] 删除消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@message_router.get("/stats")
async def get_message_stats(token_info: dict = Depends(verify_token)):
    """获取消息统计"""
    try:
        from src.services.database import get_db
        conn = get_db()
        cursor = conn.cursor()

        # 按来源统计
        cursor.execute("""
            SELECT source, COUNT(*) as count
            FROM unified_messages
            GROUP BY source
        """)
        source_stats = cursor.fetchall()

        # 今日统计
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM unified_messages WHERE DATE(created_at) = ?", (today,))
        today_count = cursor.fetchone()[0]

        conn.close()

        stats = {}
        for row in source_stats:
            stats[row[0]] = row[1]

        return {"code": 200, "data": {"by_source": stats, "today": today_count}}
    except Exception as e:
        logger.error(f"[Admin] 获取消息统计失败: {e}")
        return {"code": 200, "data": {"by_source": {}, "today": 0}}


@message_router.post("/test/link")
async def test_link_handler(
    content: str,
    source: str = "test",
    token_info: dict = Depends(verify_token)
):
    """测试链接消息处理逻辑

    Args:
        content: 消息内容（URL）
        source: 消息来源 (test/telegram/wecom)

    Returns:
        处理结果和摘要
    """
    import re
    import uuid
    from src.models.chat_record import UnifiedMessage
    from src.handlers.link import LinkHandler

    logger.info(f"[Test] 测试链接处理: {content[:100]}...")

    # 提取 URL
    url_match = re.search(r'https?://[^\s]+', content)
    if not url_match:
        raise HTTPException(status_code=400, detail="内容中未找到 URL")

    url = url_match.group(0)

    # 构建测试消息
    msg = UnifiedMessage(
        msg_id=str(uuid.uuid4()),
        source=source,
        msg_type="link",
        from_user="test_user",
        to_user="",
        content=content,
        create_time=int(datetime.now().timestamp()),
        raw_data={"link": {"title": "测试链接"}}
    )

    # 创建 handler 并处理
    handler = LinkHandler()
    await handler.handle(msg)

    # 返回处理结果
    return {
        "code": 200,
        "data": {
            "url": url,
            "msg_id": msg.msg_id,
            "status": "处理完成，请查看日志获取详细信息"
        }
    }


@message_router.post("/test/text")
async def test_text_handler(
    request: dict = None,
    content: str = None,
    source: str = "test",
    token_info: dict = Depends(verify_token)
):
    """测试文本消息处理逻辑（识别为记录类时保存到 Craft）

    Args:
        content: 消息内容 (query param)
        source: 消息来源 (query param, default: test)
        request: JSON body (可选)

    Returns:
        处理结果
    """
    import uuid
    from src.models.chat_record import UnifiedMessage
    from src.handlers.text_agent import TextAgentHandler

    # 优先使用 body 中的 content
    if request and request.get("content"):
        text_content = request.get("content")
        source = request.get("source", source)
    else:
        text_content = content

    if not text_content:
        raise HTTPException(status_code=400, detail="content 不能为空")

    logger.info(f"[Test] 测试文本处理: {text_content[:100]}...")

    # 构建测试消息
    msg = UnifiedMessage(
        msg_id=str(uuid.uuid4()),
        source=source,
        msg_type="text",
        from_user="test_user",
        to_user="",
        content=text_content,
        create_time=int(datetime.now().timestamp()),
        raw_data={}
    )

    # 创建 handler 并处理
    handler = TextAgentHandler()
    await handler.handle(msg)

    # 返回处理结果
    return {
        "code": 200,
        "data": {
            "content": text_content,
            "msg_id": msg.msg_id,
            "status": "处理完成，请查看日志确认是否保存到 Craft"
        }
    }


@message_router.post("/test/link-summary")
async def test_link_summary(
    url: str,
    token_info: dict = Depends(verify_token)
):
    """直接测试链接摘要生成

    Args:
        url: 要分析的链接

    Returns:
        生成的摘要
    """
    import requests
    from bs4 import BeautifulSoup
    from src.agents.link_summary import run_link_summary

    logger.info(f"[Test] 测试摘要生成: {url}")

    # 获取页面内容
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = resp.apparent_encoding

        soup = BeautifulSoup(resp.text, 'html.parser')

        # 提取标题
        title = soup.title.string.strip() if soup.title and soup.title.string else "未知标题"

        # 移除噪音元素
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # 提取正文
        page_content = soup.get_text(separator=' ', strip=True)

        # 生成摘要
        summary = run_link_summary(url, page_content, title)

        return {
            "code": 200,
            "data": {
                "url": url,
                "title": title,
                "content_length": len(page_content),
                "summary": summary,
                "summary_length": len(summary) if summary else 0
            }
        }
    except Exception as e:
        logger.error(f"[Test] 摘要生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
