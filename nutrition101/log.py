from itertools import zip_longest
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

    def _format_exception(self, record: LogRecord, char_limit: int) -> str:
        assert record.exc_info is not None
        default_formatter = Formatter()
        formatted_exc = default_formatter.formatException(record.exc_info)
        if len(formatted_exc) <= char_limit:
            return formatted_exc
        tb_lines = formatted_exc.splitlines()

        head, tail, chars_left = [], [], char_limit
        h1, h2 = tb_lines[: len(tb_lines) // 2], tb_lines[len(tb_lines) // 2 :]
        for l1, l2 in zip_longest(h1, reversed(h2), fillvalue=""):
            if len(l1) <= chars_left:
                head.append(l1)
                chars_left -= len(l1)
            if len(l2) <= chars_left:
                tail.append(l2)
                chars_left -= len(l2)
            if chars_left <= 10:
                head.append("....")
                break
        return "\n".join(head + list(reversed(tail)))

    def _ensure_client_started(self):
        if not self._client.is_connected():
            self._client.start(bot_token=self._bot_token)

    def emit(self, record: LogRecord) -> None:
        self._ensure_client_started()
        msg = f"{record.getMessage()}\n"
        if record.exc_info:
            traceback = self._format_exception(record, 4096 - len(msg))
            msg += f"```\n{traceback}```"
        self._client.send_message(self._group_id, msg)


class DebuggingHandler(StreamHandler):
    def _format_exception(self, record: LogRecord, char_limit: int) -> str:
        assert record.exc_info is not None
        default_formatter = Formatter()
        formatted_exc = default_formatter.formatException(record.exc_info)
        if len(formatted_exc) <= char_limit:
            return formatted_exc
        tb_lines = formatted_exc.splitlines()

        head, tail, chars_left = [], [], char_limit
        h1, h2 = tb_lines[: len(tb_lines) // 2], tb_lines[len(tb_lines) // 2 :]
        for l1, l2 in zip_longest(h1, reversed(h2), fillvalue=""):
            if len(l1) <= chars_left:
                head.append(l1)
                chars_left -= len(l1)
            if len(l2) <= chars_left:
                tail.append(l2)
                chars_left -= len(l2)
            if chars_left <= 10:
                head.append("....")
                break
        return "\n".join(head + list(reversed(tail)))

    def emit(self, record: LogRecord) -> None:
        msg = f"{record.getMessage()}\n"
        if record.exc_info:
            traceback = self._format_exception(record, 4096 - len(msg))
            msg += traceback
        from ipdb import set_trace

        set_trace()
        stream = self.stream
        stream.write(msg + self.terminator)
        self.flush()
