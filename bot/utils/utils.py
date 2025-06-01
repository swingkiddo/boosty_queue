from datetime import datetime, timezone, timedelta

def get_current_time():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def adapt_db_datetime(time: datetime):
    return time.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=3)))
