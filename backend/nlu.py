import re
from datetime import datetime, timedelta

# 中文数字小时转换
def chinese_to_digit(chinese_num):
    cn_num = {'零':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
    if chinese_num == "十":
        return 10
    if chinese_num.startswith("十"):  # 11-19
        return 10 + cn_num.get(chinese_num[1],0)
    elif "十" in chinese_num:  # 20-29
        parts = chinese_num.split("十")
        return cn_num.get(parts[0],0)*10 + (cn_num.get(parts[1],0) if parts[1] else 0)
    else:
        return cn_num.get(chinese_num,0)

# 中文分钟转换
def chinese_minute_to_digit(text):
    if not text:
        return 0
    if "半" in text:
        return 30
    elif "一刻" in text:
        return 15
    elif "三刻" in text:
        return 45
    else:
        match = re.search(r'([零一二三四五六七八九十\d]{1,3})分', text)
        if match:
            val = match.group(1)
            if val.isdigit():
                return int(val)
            else:
                return chinese_to_digit(val)
    return 0

# 解析单个时间
def parse_chinese_time(time_text: str, base_date=None):
    now = base_date or datetime.now()
    original_text = time_text

    # 中文数字小时转阿拉伯数字
    time_text = re.sub(r'[零一二三四五六七八九十]+', lambda m: str(chinese_to_digit(m.group())), time_text)

    # 匹配小时和分钟
    match = re.search(r'(\d{1,2})点(半|一刻|三刻|(\d{1,2})分)?', time_text)
    hour = now.hour
    minute = now.minute
    if match:
        hour = int(match.group(1))
        minute = 0
        if match.group(2):
            if match.group(2) in ["半","一刻","三刻"]:
                minute = chinese_minute_to_digit(match.group(2))
            elif match.group(3):
                minute = int(match.group(3))

    # 判断上午/下午/晚上
    if "下午" in time_text or "晚上" in time_text:
        if hour < 12:
            hour += 12
    elif "上午" in time_text:
        if hour == 12:
            hour = 0

    # 日期关键词
    date = now
    if "明天" in time_text:
        date += timedelta(days=1)
    elif "后天" in time_text:
        date += timedelta(days=2)
    elif m := re.search(r"星期([一二三四五六日])", time_text):
        weekdays = {"一":0,"二":1,"三":2,"四":3,"五":4,"六":5,"日":6}
        target = weekdays[m.group(1)]
        days_ahead = (target - now.weekday() + 7) % 7
        days_ahead = days_ahead if days_ahead !=0 else 7
        date += timedelta(days=days_ahead)

    dt = datetime(date.year, date.month, date.day, hour, minute)
    return dt

# 解析事件
def parse_event(text: str):
    # 匹配时间范围
    time_range_pattern = r'((今天|明天|后天|星期[一二三四五六日])?(上午|下午|晚上)?[零一二三四五六七八九十\d]{1,2}点(半|一刻|三刻|(\d{1,2})分)?)\s*(到|至|-)\s*((上午|下午|晚上)?[零一二三四五六七八九十\d]{1,2}点(半|一刻|三刻|(\d{1,2})分)?)'
    m = re.search(time_range_pattern, text)
    if m:
        start_text = m.group(1)
        end_text = m.group(7)
        start_dt = parse_chinese_time(start_text)
        end_dt = parse_chinese_time(end_text, base_date=start_dt)
        # 如果 end 小于 start 且没有标记 AM/PM，则加 12 小时
        if end_dt <= start_dt and not re.search(r"(上午|下午|晚上)", end_text):
            end_dt += timedelta(hours=12)
        title = text.replace(m.group(), "").strip()
    else:
        # 单时间
        single_time_pattern = r'((今天|明天|后天|星期[一二三四五六日])?(上午|下午|晚上)?[零一二三四五六七八九十\d]{1,2}点(半|一刻|三刻|(\d{1,2})分)?)'
        m2 = re.search(single_time_pattern, text)
        if m2:
            start_dt = parse_chinese_time(m2.group(1))
            end_dt = start_dt + timedelta(hours=1)
            title = text.replace(m2.group(), "").strip()
        else:
            start_dt = datetime.now()
            end_dt = start_dt + timedelta(hours=1)
            title = text

    # 清理标题
    title = re.sub(r"(有|安排|事件)", "", title).strip()
    if not title:
        title = "语音日程"

    return {
        "title": title,
        "date": start_dt.strftime("%Y-%m-%d"),
        "start_time": start_dt.strftime("%H:%M"),
        "end_time": end_dt.strftime("%H:%M"),
        "description": text
    }
