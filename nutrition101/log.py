from logging import Handler, LogRecord, StreamHandler, Formatter

from telethon.sync import TelegramClient


class TelegramLogHandler(Handler):
    def __init__(
        self, api_id: int, api_hash: str, bot_token: str, group_id: int, session: str
    ):
        self._bot_token = bot_token
        self._group_id = group_id
        self._client = TelegramClient(session=session, api_id=api_id, api_hash=api_hash)
        super().__init__()

    def _ensure_client_started(self):
        if not self._client.is_connected():
            self._client.start(bot_token=self._bot_token)

    def emit(self, record: LogRecord) -> None:
        self._ensure_client_started()
        msg = record.getMessage()
        if record.exc_info:
            msg = f"{msg}\n```{Formatter().formatException(record.exc_info)}```"
        self._client.send_message(self._group_id, msg)


class DebuggingHandler(StreamHandler):
    def emit(self, record: LogRecord) -> None:
        msg = self.format(record)
        print("WATAFA")
        from ipdb import set_trace

        set_trace()
        return super().emit(record)
