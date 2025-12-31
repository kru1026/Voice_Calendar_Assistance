import time
import re
from playwright.sync_api import sync_playwright, expect
from nlu import parse_event
import pyttsx3 
import speech_recognition as sr
from datetime import datetime, timedelta

DEBUG_PORT = 9222

def speak_message(message):
    print("[DEBUG] Initializing TTS engine")
    engine = pyttsx3.init()

    # List available voices
    voices = engine.getProperty('voices')
    print(f"[DEBUG] Found {len(voices)} voices")

    for v in voices:
        print("[VOICE]", v.id, v.name, v.languages)

    # Choose a voice that supports Chinese
    zh_voice = None
    for v in voices:
        if "zh" in v.id.lower() or "chinese" in v.name.lower():
            zh_voice = v.id
            print(f"[DEBUG] Using Chinese voice: {v.name}")
            break

    if zh_voice:
        engine.setProperty('voice', zh_voice)
    else:
        print("[WARN] No Chinese voice found, using default")

    print("[DEBUG] Speaking message:", message)
    engine.say(message)
    engine.runAndWait()


def time_to_minutes(time_str):
    """Convert time string like '10:00am', '14:30', or '2pm' to minutes since midnight."""
    time_str = time_str.strip().lower()

    # Remove spaces
    time_str = time_str.replace(" ", "")

    # Match hour:minute
    match = re.match(r'(\d{1,2})(?::(\d{2}))?(am|pm)?', time_str)
    if not match:
        return 0  # fallback

    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    meridiem = match.group(3)

    if meridiem == "pm" and hour != 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0

    return hour * 60 + minute

def extract_event_times(label):
    """
    Extract start and end times from Google Calendar aria-label.
    Handles:
        - 10:00am – 11:00am
        - 2–3pm
        - 14:00–15:00
    """
    if not label:
        return None, None

    # Match hour-only or hour:minute with optional am/pm
    match = re.search(r'(\d{1,2}(?::\d{2})?(?:am|pm)?)\s*–\s*(\d{1,2}(?::\d{2})?(?:am|pm)?)', label, re.I)
    if match:
        return match.group(1), match.group(2)
    return None, None

import re

def is_slot_occupied(page, date, start_time, end_time):
    """
    Check if a time slot is occupied in Google Calendar.
    
    Parameters:
        page: Playwright page object
        start_time, end_time: datetime objects representing the slot to check
    
    Returns:
        True if any event overlaps the slot, False otherwise
    """
    start_time_obj = datetime.strptime(start_time, "%H:%M")
    end_time_obj = datetime.strptime(end_time, "%H:%M")

    start_min = start_time_obj.hour * 60 + start_time_obj.minute
    end_min = end_time_obj.hour * 60 + end_time_obj.minute

    # select all gridcell divs with aria-labels
    gridcells = page.query_selector_all('div[role="gridcell"] div[aria-label]')
    for e in gridcells:
        label = e.get_attribute('aria-label')
        if not label:
            continue

        # normalize label
        label = label.replace("\n", " ").strip()
        label = label.replace("–", "-").replace("—", "-")  # normalize dashes
        if "-" not in label:
            continue

        parts = label.split("-")
        if len(parts) < 2:
            continue

        event_start_str = parts[0].strip()
        event_end_str = parts[1].strip().split()[0]  # remove event title if present

        def parse_time_string(s):
            """
            Convert a string like '2', '2pm', '2:30pm', '14:30' to minutes since midnight
            """
            s = s.lower().replace("am"," am").replace("pm"," pm").strip()
            match = re.match(r"(\d{1,2})(?::(\d{1,2}))?\s*(am|pm)?", s)
            if not match:
                return None
            h = int(match.group(1))
            m = int(match.group(2)) if match.group(2) else 0
            meridiem = match.group(3)
            if meridiem == "pm" and h < 12:
                h += 12
            if meridiem == "am" and h == 12:
                h = 0
            return h*60 + m

        event_start_min = parse_time_string(event_start_str)
        event_end_min = parse_time_string(event_end_str)

        if event_start_min is None or event_end_min is None:
            continue

        # overlap check
        if start_min < event_end_min and end_min > event_start_min:
            return True

    return False








def round_down_24h_to_pre_15mins(time_24h: str) -> str:
    """
    Convert 24-hour time string (HH:MM) to Google Calendar format,
    rounding down to previous 15-minute interval.
    """
    # Parse 24-hour time
    dt = datetime.strptime(time_24h, "%H:%M")
    
    # Floor minutes to previous 15-minute interval
    floored_minute = (dt.minute // 15) * 15
    dt = dt.replace(minute=floored_minute, second=0)
    
    # Format for Google Calendar: h:mmam/pm (lowercase, no space)
    # Use %-I on Linux/macOS; on Windows use %I and strip leading zero
    return dt.strftime("%I:%M%p").lstrip("0").lower()

def round_up_24h_to_next_30mins(time_24h: str) -> str:
    """
    Convert 24-hour time string (HH:MM) to Google Calendar format,
    rounding UP to the next 30-minute interval.
    """
    dt = datetime.strptime(time_24h, "%H:%M")
    
    # Round minutes up to next 30-minute interval
    minute = dt.minute
    if minute == 0 or minute <= 30:
        dt = dt.replace(minute=30 if minute > 0 else 0, second=0)
        if minute > 30:
            dt += timedelta(hours=1)
            dt = dt.replace(minute=0)
    # Actually simpler using math:
    # dt += timedelta(minutes=(30 - dt.minute % 30) % 30)

    # Format for Google Calendar: h:mmam/pm (lowercase, no space)
    return dt.strftime("%I:%M%p").lstrip("0").lower()


def get_voice_input(prompt="请说新的时间："):
    print(prompt)
    speak_message(prompt)  # 可选：用 TTS 语音播报提示
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("[DEBUG] Listening...")
        audio = r.listen(source)  # 会自动结束在短暂停顿后
    try:
        text = r.recognize_google(audio, language="zh-CN")  # 中文识别
        print("[DEBUG] Recognized text:", text)
        return text
    except sr.UnknownValueError:
        print("[ERROR] 无法识别语音，请重试。")
        return get_voice_input(prompt)  # 递归重新听
    except sr.RequestError as e:
        print(f"[ERROR] 语音识别服务出错: {e}")
        return None


def add_event_to_calendar(initial_event):
    """循环检查时间，直到没有冲突再创建日程"""
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}")

        # 获取已有的上下文（Chrome 默认会有一个）
        context = browser.contexts[0]

        # 新建或复用页面
        page = context.new_page()

        page.goto("https://calendar.google.com", wait_until="load")
        print(page.title())

        # 等待手动登录
        while page.query_selector('input[type="email"]') or "accounts.google.com" in page.url:
            speak_message("Google 登录已过期，请重新登录。")
            print("[DEBUG] Waiting for user to login...")
            time.sleep(15)
            page.goto("https://calendar.google.com")

        print("[DEBUG] Logged in successfully, continuing to create event")

        event = initial_event 
        while True:
            #occupied = is_slot_occupied(page, event["date"], event["start_time"], event["end_time"])
            occupied = True
            if occupied:
                # 提示用户换时间
                msg = f"您在{event['date']} {event['start_time']}到{event['end_time']}已有日程安排，请说新的时间。"
                print("[WARN]", msg)
                speak_message(msg)

                # 等待用户语音输入新时间
                new_text = get_voice_input("请说新的时间描述：")
                if new_text:
                    event = parse_event(new_text)
            else:
                page.locator('button:has-text("Create"), button:has-text("创建")').first.click()
                page.wait_for_timeout(300)
                print("Create clicked")

                 # Click "Event" (English or Chinese)
                event_locator = page.locator('div:has-text("Event"), div:has-text("事件")').first
                event_locator.wait_for(state="visible", timeout=5000)
                event_locator.click()

                print("Clicked 'Event' successfully!")

                page.fill('input[aria-label="Add title"], input[aria-label="添加标题"]', event["title"])
                print("title filled")

                page.locator('button:has-text("More options")').first.click()
                page.wait_for_timeout(300)
                print("More options clicked")

                print("date is: ", event["date"])

                page.get_by_label("Start date").click()
                # Suppose event["date"] = "2025-12-31"
                date_obj = datetime.strptime(event["date"], "%Y-%m-%d")
                date_str = date_obj.strftime("%Y%m%d")
                print(date_str)
               
                # select the td representing the date
                day_cell = page.locator(f'td[data-date="{date_str}"]:not([data-dragsource-type])')

                # wait until visible, scroll if needed
                day_cell.wait_for(state="visible")
                day_cell.scroll_into_view_if_needed()

                # click it
                day_cell.click()



                print("day selected")

                # # Get the Start time combobox input and click it
                start_time_input = page.get_by_role("combobox", name="Start time")
                start_time_input.click()

                start_time = round_down_24h_to_pre_15mins(event["start_time"])
                print(start_time)
                page.get_by_role("option", name=start_time).click()

                end_time_input = page.get_by_role("combobox", name="End time")
                end_time_input.click()
                end_time = round_up_24h_to_next_30mins(event["end_time"])
                print(event["end_time"])
                print(end_time)
                page.get_by_role("option", name=end_time).click()

                #page.get_by_label("End date").click()
                # Suppose event["date"] = "2025-12-31"
                # date_obj 是开始日期
                date_obj2 = datetime.strptime(event["date"], "%Y-%m-%d")
                if event["start_time"] > event["end_time"]:
                    end_date_obj = date_obj2 + timedelta(days=1)  # 增加一天
                else:
                    end_date_obj = date_obj2

                date_str2 = end_date_obj.strftime("%Y%m%d")  

                print("end date is ", date_str2)

                # day_cell2 = page.locator(
                #     f'td[data-date="{date_str2}"] [role="gridcell"]'
                # )
                # day_cell2.wait_for(state="visible")
                # day_cell2.scroll_into_view_if_needed()
                # day_cell2.click()

                
                page.get_by_label("End date").click()
                
                # select the td representing the date
                # day_cell2 = page.locator(f'td[data-date="{date_str2}"]:not([data-dragsource-type])')

                # # wait until visible, scroll if needed
                # day_cell2.wait_for(state="visible")
                # day_cell2.scroll_into_view_if_needed()

                # # click it
                # day_cell2.click()

                page.get_by_role("gridcell", name="31").click()





                
                #page.get_by_role("gridcell", name=day_str2).filter(has_text=month_name).click()
                print("day selected")

                page.locator('button:has-text("Save")').first.click()
                break

