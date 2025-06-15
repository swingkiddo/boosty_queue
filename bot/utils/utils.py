from datetime import datetime, timezone, timedelta

def get_current_time():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def adapt_db_datetime(time: datetime):
    return time.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=3)))

def format_duration(seconds: int) -> str:
    hours = int(seconds // 3600)
    if hours < 10:
        hours = f"0{hours}"
    minutes = int((seconds % 3600) // 60)
    if minutes < 10:
        minutes = f"0{minutes}"
    seconds = int(seconds % 60)
    if seconds < 10:
        seconds = f"0{seconds}"
    duration_str = f"{hours}:{minutes}:{seconds}"
    return duration_str