import configparser
import logging
import os

from nutrition101.models import ClaudeNAnalyzer, GrokAnalyzer
from nutrition101.log import TelegramLogHandler, DebuggingHandler


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


def _configure_logging_debug():
    logger = logging.getLogger("n101")
    logging.basicConfig(level=logging.INFO)
    logger.addHandler(DebuggingHandler())


CONFIG = configparser.ConfigParser()
CONFIG.read("config.ini")

CLAUDE_LLM = ClaudeNAnalyzer(api_key=CONFIG["LLM"]["ANTHROPIC_API_KEY"])
GROK_LLM = GrokAnalyzer(api_key=CONFIG["LLM"]["GROK_API_KEY"])

if os.environ.get("DEBUG_LOGS"):
    _configure_logging_debug()
else:
    _configure_logging()
