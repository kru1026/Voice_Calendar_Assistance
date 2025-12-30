import time
import re
from playwright.sync_api import sync_playwright
from nlu import parse_event
import pyttsx3 
import speech_recognition as sr
from playwright.sync_api import expect
from datetime import datetime

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
    """Convert 12-hour time string like '10:30am' or '2:15pm' to minutes since midnight."""
    m = re.match(r'(\d+):?(\d{0,2})\s*(am|pm)', time_str.lower())
    if not m:
        return 0
    h, minute, period = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if period == 'pm' and h != 12:
        h += 12
    if period == 'am' and h == 12:
        h = 0
    return h * 60 + minute

def is_slot_occupied(page, date, start_time, end_time):
    """Check if a time slot is already occupied in Google Calendar."""
    # Go to the specific day view
    page.goto(f"https://calendar.google.com/calendar/r/day/{date.replace('-', '/')}")
    time.sleep(3)  # wait for full render

    start_min = time_to_minutes(start_time)
    end_min = time_to_minutes(end_time)

    # Select **all divs in the main calendar grid that contain a dash in the aria-label**
    # Usually event labels are like "10:00am – 11:00am Event Title"
    events = page.query_selector_all('div[role="gridcell"] div[aria-label*="–"]')

    for e in events:
        label = e.get_attribute('aria-label')
        if not label:
            continue

        # Split start and end time from the label
        parts = label.split('–')
        if len(parts) < 2:
            continue

        event_start_str = parts[0].strip()
        # The end time may be followed by event title, take first word
        event_end_str = parts[1].strip().split()[0]

        event_start_min = time_to_minutes(event_start_str)
        event_end_min = time_to_minutes(event_end_str)

        # Check for overlap
        if start_min < event_end_min and end_min > event_start_min:
            return True  # slot is occupied

    return False  # slot is free


def round_down_24h_to_gc(time_24h: str) -> str:
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
            occupied = is_slot_occupied(page, event["date"], event["start_time"], event["end_time"])
            if occupied:
                # 提示用户换时间
                msg = f"您在{event['date']} {event['start_time']}到{event['end_time']}已有日程安排：{conflict_label}，请说新的时间。"
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
                day_str = str(date_obj.day)  # "31"
                page.get_by_role("gridcell", name=day_str).click()
                print("day selected")

                # # Get the Start time combobox input and click it
                start_time_input = page.get_by_role("combobox", name="Start time")
                start_time_input.click()

                start_time = round_down_24h_to_gc(event["start_time"])
                print(start_time)
                page.get_by_role("option", name=start_time).click()

                end_time_input = page.get_by_role("combobox", name="End time")
                end_time_input.click()
                end_time = round_down_24h_to_gc(event["end_time"])
                print(end_time)
                page.get_by_role("option", name=end_time).click()

                page.get_by_label("End date").click()
                # Suppose event["date"] = "2025-12-31"
                date_obj2 = datetime.strptime(event["date"], "%Y-%m-%d")
                day_str2 = str(date_obj2.day)  # "31"
                page.get_by_role("gridcell", name=day_str2).click()
                print("day selected")

                page.locator('button:has-text("Save")').first.click()
                break



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
