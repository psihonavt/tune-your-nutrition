import configparser
import logging

from nutrition101.models import ClaudeNAnalyzer
from nutrition101.log import TelegramLogHandler


def _configure_logging():
    logger = logging.getLogger("n101")
    logging.basicConfig(level=logging.INFO)
    t_handler = TelegramLogHandler(
        session=CONFIG["Telegram"]["TELETHON_SESSION_NAME"],
        api_id=int(CONFIG["Telegram"]["API_ID"]),
        api_hash=CONFIG["Telegram"]["API_HASH"],
        group_id=int(CONFIG["Telegram"]["LOG_TO_GROUP_ID"]),
        bot_token=CONFIG["Telegram"]["BOT_TOKEN"],
    )
    logger.addHandler(t_handler)


CONFIG = configparser.ConfigParser()
CONFIG.read("config.ini")

LLM = ClaudeNAnalyzer(api_key=CONFIG["LLM"]["ANTHROPIC_API_KEY"])

_configure_logging()
