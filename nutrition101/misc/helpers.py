import zoneinfo
from datetime import datetime, date


def get_today_date(timezone="America/Los_Angeles") -> date:
    return datetime.now().astimezone(zoneinfo.ZoneInfo(timezone)).date()
