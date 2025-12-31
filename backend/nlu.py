import re
from datetime import datetime, timedelta

# =========================
# 中文数字转换
# =========================
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


# =========================
# 解析单个时间点
# =========================
def parse_chinese_time(time_text: str, base_date=None):
    now = base_date or datetime.now()
    date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # ---------- 日期 ----------
    if "明天" in time_text:
        date += timedelta(days=1)
    elif "后天" in time_text:
        date += timedelta(days=2)
    else:
        m = re.search(r"星期([一二三四五六日])", time_text)
        if m:
            weekdays = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6}
            target = weekdays[m.group(1)]
            delta = (target - now.weekday() + 7) % 7
            delta = delta if delta != 0 else 7
            date += timedelta(days=delta)

    # ---------- 中文数字替换 ----------
    time_text = re.sub(
        r'[零一二三四五六七八九十\d]+',
        lambda m: str(chinese_to_digit(m.group())),
        time_text
    )

    # ---------- 时间 ----------
    hour, minute = 0, 0
    m = re.search(r'(\d{1,2})点(半|一刻|三刻|(\d{1,2})分)?', time_text)
    if m:
        hour = int(m.group(1))
        minute = chinese_minute_to_digit(m.group(2))

    # ---------- 时段修正 ----------
    if "凌晨" in time_text:
        if hour == 12:
            hour = 0
        date += timedelta(days=1)
    elif "晚上" in time_text or "下午" in time_text:
        if hour < 12:
            hour += 12
    elif "上午" in time_text:
        if hour == 12:
            hour = 0

    return datetime(date.year, date.month, date.day, hour, minute)


# =========================
# 解析事件（核心）
# =========================
def parse_event(text: str):
    time_range_pattern = (
        r'((今天|明天|后天|星期[一二三四五六日])?'
        r'(上午|下午|晚上|凌晨)?'
        r'[零一二三四五六七八九十\d]{1,2}点'
        r'(半|一刻|三刻|(\d{1,2})分)?)'
        r'\s*(到|至|-)\s*'
        r'((上午|下午|晚上|凌晨)?'
        r'[零一二三四五六七八九十\d]{1,2}点'
        r'(半|一刻|三刻|(\d{1,2})分)?)'
    )

    m = re.search(time_range_pattern, text)

    if m:
        start_text = m.group(1)
        end_text = m.group(7)

        # ---------- 时段继承 ----------
        start_period = re.search(r'(上午|下午|晚上|凌晨)', start_text)
        end_period = re.search(r'(上午|下午|晚上|凌晨)', end_text)
        if not end_period and start_period:
            end_text = start_period.group() + end_text

        # ---------- 解析时间 ----------
        start_dt = parse_chinese_time(start_text)
        end_dt = parse_chinese_time(end_text, base_date=start_dt)

        # ⭐ 跨天判断（如果用户明确是隔天才加天）
        if end_dt <= start_dt and not re.search(r'(明天|后天|星期)', end_text):
            # 不自动跨天，保持原时间
            pass

        title = text.replace(m.group(), "").strip()

    else:
        # ---------- 单时间 ----------
        single_time_pattern = (
            r'((今天|明天|后天|星期[一二三四五六日])?'
            r'(上午|下午|晚上|凌晨)?'
            r'[零一二三四五六七八九十\d]{1,2}点'
            r'(半|一刻|三刻|(\d{1,2})分)?)'
        )
        m2 = re.search(single_time_pattern, text)
        if m2:
            start_dt = parse_chinese_time(m2.group(1))
            end_dt = start_dt + timedelta(hours=1)
            title = text.replace(m2.group(), "").strip()
        else:
            start_dt = datetime.now()
            end_dt = start_dt + timedelta(hours=1)
            title = text

    # ---------- 清理标题 ----------
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


