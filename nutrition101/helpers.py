import zoneinfo
from datetime import datetime


def get_today_date(timezone="America/Los_Angeles") -> datetime:
    return datetime.now().astimezone(zoneinfo.ZoneInfo(timezone))
