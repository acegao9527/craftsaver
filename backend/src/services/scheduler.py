import logging
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from src.api.routers.news import process_news_generation_task
from src.services.todo_reminder import get_remind_time, is_todo_enabled

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def run_birthday_check():
    """Wrapper to run async birthday check"""
    from src.birthday_reminder.service import BirthdayService
    asyncio.run(BirthdayService.check_and_notify())


def run_todo_reminder_wrapper():
    """Wrapper to run async todo reminder"""
    from src.services.todo_reminder import run_todo_reminder
    asyncio.run(run_todo_reminder())


def run_douban_scraper():
    """Wrapper to run douban scraper"""
    from src.services.douban_scraper import run_scraper
    run_scraper()


def parse_remind_time():
    """解析提醒时间配置"""
    time_str = get_remind_time()
    try:
        hour, minute = time_str.split(":")
        return int(hour), int(minute)
    except (ValueError, AttributeError):
        return 9, 0


def start_scheduler():
    """
    启动定时任务调度器
    """
    # 添加定时任务：每周二 12:00, 12:05, 12:10 执行
    # 注意：时区依赖于系统配置或 Docker TZ 环境变量 (设置为 Asia/Shanghai)

    times = [0, 5, 10]

    for minute in times:
        scheduler.add_job(
            process_news_generation_task,
            CronTrigger(day_of_week='tue', hour=12, minute=minute),
            id=f"news_job_{minute}",
            name=f"News Generation Task (Tue 12:{minute:02d})",
            replace_existing=True
        )
        logger.info(f"[Scheduler] 已添加任务: 每周二 12:{minute:02d} 生成新闻")

    # 每天 09:00 检查生日提醒
    scheduler.add_job(
        run_birthday_check,
        CronTrigger(hour=9, minute=0),
        id="birthday_check_job",
        name="Birthday Reminder Check (Daily 09:00)",
        replace_existing=True
    )
    logger.info("[Scheduler] 已添加任务: 每天 09:00 检查生日提醒")

    # Craft 待办提醒
    if is_todo_enabled():
        hour, minute = parse_remind_time()
        scheduler.add_job(
            run_todo_reminder_wrapper,
            CronTrigger(hour=hour, minute=minute),
            id="todo_reminder_job",
            name=f"Craft Todo Reminder (Daily {hour:02d}:{minute:02d})",
            replace_existing=True
        )
        logger.info(f"[Scheduler] 已添加任务: 每天 {hour:02d}:{minute:02d} 发送 Craft 待办提醒")
    else:
        logger.info("[Scheduler] Craft 待办提醒未启用，跳过")

    # 每天 02:00 爬取豆瓣观看记录
    scheduler.add_job(
        run_douban_scraper,
        CronTrigger(hour=2, minute=0),
        id="douban_scraper_job",
        name="Douban Movie Scraper (Daily 02:00)",
        replace_existing=True
    )
    logger.info("[Scheduler] 已添加任务: 每天 02:00 爬取豆瓣观看记录")

    try:
        scheduler.start()
        logger.info("[Scheduler] 定时任务调度器已启动")
    except Exception as e:
        logger.error(f"[Scheduler] 启动失败: {e}")

def shutdown_scheduler():
    """
    关闭调度器
    """
    scheduler.shutdown()
    logger.info("[Scheduler] 定时任务调度器已关闭")
