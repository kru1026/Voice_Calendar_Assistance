import re
import dateparser
from datetime import datetime, timedelta

def parse_event(text: str):
    # 尝试匹配时间关键字
    match = re.search(r"(今天|明天|后天)?(上午|下午|晚上)?\d{1,2}点", text)
    if match:
        start_date = dateparser.parse(match.group(), languages=["zh"])
    else:
        start_date = dateparser.parse(text, languages=["zh"])

    # 如果解析失败，使用当前时间作为 fallback
    if start_date is None:
        start_date = datetime.now()

    # 给结束时间 +1 小时
    end_date = start_date + timedelta(hours=1)

    return {
        "title": "语音日程",
        "date": start_date.strftime("%Y-%m-%d"),
        "start_time": start_date.strftime("%H:%M"),
        "end_time": end_date.strftime("%H:%M"),
        "description": text
    }
