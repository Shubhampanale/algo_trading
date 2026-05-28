from datetime import datetime
from zoneinfo import ZoneInfo


def get_ist_now():
    return datetime.now(ZoneInfo("Asia/Kolkata"))