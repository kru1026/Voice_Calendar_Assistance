import re
from datetime import datetime, timedelta

# -------------------------
# 中文数字转换
# -------------------------
def chinese_to_digit(chinese_num):
    cn_num = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
    }

    if chinese_num.isdigit():
        return int(chinese_num)

    if chinese_num == "十":
        return 10
    if chinese_num.startswith("十"):  # 11-19
        return 10 + cn_num.get(chinese_num[1], 0)
    if "十" in chinese_num:  # 20-99
        left, right = chinese_num.split("十")
        return cn_num.get(left, 0) * 10 + cn_num.get(right, 0)
    return cn_num.get(chinese_num, 0)


def chinese_minute_to_digit(text):
    if not text:
        return 0
    if "半" in text:
        return 30
    if "一刻" in text:
        return 15
    if "三刻" in text:
        return 45

    m = re.search(r'([零一二三四五六七八九十\d]{1,3})分', text)
    if m:
        return chinese_to_digit(m.group(1))
    return 0

# -------------------------
# 解析单个时间点
# -------------------------
def parse_chinese_time(time_text: str, base_date=None, inherit_period=None):
    now = datetime.now()
    date = base_date or now

    # ---------- Normalize spaces ----------
    time_text = time_text.replace("\u3000", "").replace("\xa0", "").strip()

    # ---------- Detect date keyword ----------
    if time_text.startswith("明天"):
        date = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        time_text = time_text[len("明天"):].lstrip()
    elif time_text.startswith("后天"):
        date = (now + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        time_text = time_text[len("后天"):].lstrip()
    elif time_text.startswith("今天"):
        date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        time_text = time_text[len("今天"):].lstrip()

    # ---------- Detect period ----------
    m_period = re.search(r'(上午|下午|早上|晚上|凌晨)', time_text)
    period = m_period.group() if m_period else inherit_period

    # ---------- Extract hour and minute ----------
    hour, minute = 0, 0
    m_time = re.search(r'([零一二三四五六七八九十\d]{1,2})点(半|一刻|三刻|(\d{1,2})分)?', time_text)
    if m_time:
        hour_text = m_time.group(1)
        hour = chinese_to_digit(hour_text)
        minute = chinese_minute_to_digit(m_time.group(2))

    # ---------- Adjust hour for period ----------
    if period:
        if period in ["下午", "晚上"] and hour < 12:
            hour += 12
        if period in ["上午", "凌晨", "早上"] and hour == 12:
            hour = 0

    return datetime(date.year, date.month, date.day, hour, minute)

# -------------------------
# 解析事件
# -------------------------
def parse_event(text: str):
    # ---------- Match time range ----------
    time_range_pattern = (
        r'((今天|明天|后天|星期[一二三四五六日])?'
        r'(上午|下午|早上|晚上|凌晨)?'
        r'[零一二三四五六七八九十\d]{1,2}点'
        r'(半|一刻|三刻|(\d{1,2})分)?)'
        r'\s*(到|至|-)\s*'
        r'((上午|下午|早上|晚上|凌晨)?'
        r'[零一二三四五六七八九十\d]{1,2}点'
        r'(半|一刻|三刻|(\d{1,2})分)?)'
    )

    m = re.search(time_range_pattern, text)
    if m:
        start_text = m.group(1)
        end_text = m.group(7)

        # ---------- Period inheritance ----------
        start_period_match = re.search(r'(上午|下午|早上|晚上|凌晨)', start_text)
        start_period = start_period_match.group() if start_period_match else None

        start_dt = parse_chinese_time(start_text, inherit_period=start_period)
        end_dt = parse_chinese_time(end_text, base_date=start_dt, inherit_period=start_period)

        # ---------- Prevent accidental cross-day ----------
        if end_dt <= start_dt and not re.search(r'(明天|后天|星期)', end_text):
            # do not automatically cross day
            pass

        title = text.replace(m.group(), "").strip()
    else:
        # ---------- Single time ----------
        single_time_pattern = (
            r'((今天|明天|后天|星期[一二三四五六七八九十\d])?'
            r'(上午|下午|早上|晚上|凌晨)?'
            r'[零一二三四五六七八九十\d]{1,2}点'
            r'(半|一刻|三刻|(\d{1,2})分)?)'
        )
        m2 = re.search(single_time_pattern, text)
        if m2:
            start_period_match = re.search(r'(上午|下午|早上|晚上|凌晨)', m2.group())
            start_period = start_period_match.group() if start_period_match else None

            start_dt = parse_chinese_time(m2.group(1), inherit_period=start_period)
            end_dt = start_dt + timedelta(hours=1)
            title = text.replace(m2.group(), "").strip()
        else:
            start_dt = datetime.now()
            end_dt = start_dt + timedelta(hours=1)
            title = text

    # ---------- Clean title ----------
    title = re.sub(r"(有|安排|事件)", "", title).strip()
    if not title:
        title = "语音日程"

    return {
        "title": title,
        "start_date": start_dt.strftime("%Y-%m-%d"),
        "start_time": start_dt.strftime("%H:%M"),
        "end_date": end_dt.strftime("%Y-%m-%d"),
        "end_time": end_dt.strftime("%H:%M"),
        "description": text
    }
