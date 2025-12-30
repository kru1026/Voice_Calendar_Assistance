import re
from datetime import datetime, timedelta
import dateparser

def parse_event(text: str):
    print("\n[DEBUG] ===== parse_event called =====")
    print("[DEBUG] Input text:", text)

    # 中文时间关键词
    time_keywords = r"(今天|明天|后天|星期[一二三四五六日])?(上午|下午|晚上)?\d{1,2}(:\d{2})?点"
    print("[DEBUG] Time keyword regex:", time_keywords)

    # 尝试匹配时间范围
    range_pattern = rf"{time_keywords}\s*(到|-)\s*\d{{1,2}}(:\d{{2}})?"
    range_match = re.search(range_pattern, text)
    print("[DEBUG] Range regex:", range_pattern)
    print("[DEBUG] Range match:", range_match.group() if range_match else None)

    if range_match:
        print("[DEBUG] Detected time range")

        # 解析开始时间
        start_text = range_match.group().split("到")[0].split("-")[0]
        print("[DEBUG] Start time text:", start_text)

        start_date = dateparser.parse(start_text, languages=["zh"])
        print("[DEBUG] Parsed start_date:", start_date)

        # 解析结束时间
        end_text = range_match.group().split("到")[-1].split("-")[-1].strip()
        print("[DEBUG] Raw end time text:", end_text)

        if len(end_text.split(":")) == 1:
            end_text += ":00"
            print("[DEBUG] Normalized end time text:", end_text)

        end_hour, end_minute = map(int, end_text.split(":"))
        end_date = start_date.replace(hour=end_hour, minute=end_minute)
        print("[DEBUG] Parsed end_date:", end_date)

        # 移除时间部分作为标题
        title = text.replace(range_match.group(), "").strip()
        print("[DEBUG] Extracted title (range):", title)

    else:
        print("[DEBUG] No time range detected, trying single time")

        match = re.search(time_keywords, text)
        print("[DEBUG] Single time match:", match.group() if match else None)

        if match:
            start_date = dateparser.parse(match.group(), languages=["zh"])
            print("[DEBUG] Parsed start_date from match:", start_date)
        else:
            start_date = dateparser.parse(text, languages=["zh"])
            print("[DEBUG] Parsed start_date from full text:", start_date)

        if start_date is None:
            print("[WARN] dateparser failed, using current time")
            start_date = datetime.now()

        end_date = start_date + timedelta(hours=1)
        print("[DEBUG] Auto end_date (+1h):", end_date)

        # 移除时间部分作为标题
        title = text
        if match:
            title = text.replace(match.group(), "").strip()
        print("[DEBUG] Extracted title (single):", title)

    # 清理标题
    title_before = title
    title = re.sub(r"(有|安排|事件)", "", title).strip()
    print("[DEBUG] Cleaned title:", title, "(before:", title_before, ")")

    if not title:
        title = "语音日程"
        print("[DEBUG] Title empty, using default:", title)

    result = {
        "title": title,
        "date": start_date.strftime("%Y-%m-%d"),
        "start_time": start_date.strftime("%H:%M"),
        "end_time": end_date.strftime("%H:%M"),
        "description": text
    }

    print("[DEBUG] Final parsed event:", result)
    print("[DEBUG] ===== parse_event finished =====\n")

    return result
