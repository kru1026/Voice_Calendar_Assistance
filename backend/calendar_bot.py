import time
import re
from playwright.sync_api import sync_playwright, expect
from nlu import parse_event
import pyttsx3 
import speech_recognition as sr
from datetime import datetime, timedelta

DEBUG_PORT = 9222

latest_recognized_text = None

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


def is_slot_occupied(page, date, start_time, end_time):

    url = f"https://calendar.google.com/calendar/u/0/r/day/{date.replace('-', '/')}"
    page.goto(url)

    # Convert desired slot to minutes since midnight
    start_dt = datetime.strptime(start_time, "%H:%M")
    end_dt = datetime.strptime(end_time, "%H:%M")
    slot_start_min = start_dt.hour * 60 + start_dt.minute
    slot_end_min = end_dt.hour * 60 + end_dt.minute

    # ---------- Select only real grid cells ----------
    # div.XsRa1c are the actual event grid cells
    gridcells = page.query_selector_all('div.XsRa1c')

    for cell in gridcells:
        spans = cell.query_selector_all('span.wO6pL.iHNmdb')  # only event spans
        for span in spans:
            label = span.inner_text().strip()
            if not label:
                continue

            # Normalize dash and remove extra spaces/unicode
            label = re.sub(r"[–—−]", "-", label.replace("\u202f", "").replace("\xa0", ""))
            label = label.lower()

            # Skip non-time labels
            if not re.search(r"\d", label):
                continue

            # Split start and end times
            if "-" in label:
                parts = label.split("-")
                event_start_str = parts[0].strip()
                event_end_str = parts[1].strip().split()[0]  # remove title if any
            else:
                event_start_str = label
                event_end_str = None

            # Helper to convert time string to minutes since midnight
            def parse_time_string(s):
                s = s.strip().lower()
                s = re.sub(r"\s+", "", s)
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
                return h * 60 + m

            event_start_min = parse_time_string(event_start_str)
            if event_start_min is None:
                continue

            if event_end_str:
                event_end_min = parse_time_string(event_end_str)
                if event_end_min is None:
                    continue
            else:
                event_end_min = event_start_min + 30  # default duration

            # Check for overlap
            if slot_start_min < event_end_min and slot_end_min > event_start_min:
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


# def get_voice_input(prompt="请说新的时间："):
#     print(prompt)
#     speak_message(prompt)  # 可选：用 TTS 语音播报提示
#     r = sr.Recognizer()
#     with sr.Microphone() as source:
#         print("[DEBUG] Listening...")
#         audio = r.listen(source)  # 会自动结束在短暂停顿后
#     try:
#         text = r.recognize_google(audio, language="zh-CN")  # 中文识别
#         print("[DEBUG] Recognized text:", text)
#         return text
#     except sr.UnknownValueError:
#         print("[ERROR] 无法识别语音，请重试。")
#         return get_voice_input(prompt)  # 递归重新听
#     except sr.RequestError as e:
#         print(f"[ERROR] 语音识别服务出错: {e}")
#         return None


def add_event_to_calendar(initial_event, recognized_text=None):
    """
    Create a Google Calendar event, waiting for the frontend to send voice input if needed.

    Parameters:
        initial_event: dict with 'title', 'date', 'start_time', 'end_time'
        recognized_text: optional string from frontend speech recognition.
    """

    global latest_recognized_text

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}")
        context = browser.contexts[0]
        page = context.new_page()
        page.goto("https://calendar.google.com", wait_until="load")
        print("[DEBUG] Page title:", page.title())

        # Wait for manual login
        while page.query_selector('input[type="email"]') or "accounts.google.com" in page.url:
            speak_message("Google 登录已过期，请重新登录。")
            print("[DEBUG] Waiting for user login...")
            time.sleep(15)
            page.goto("https://calendar.google.com")

        print("[DEBUG] Logged in successfully, continuing to create event")

        event = initial_event
        while True:
            # Check if slot is occupied
            occupied = is_slot_occupied(page, event['start_date'], event['start_time'], event['end_time'])
    
            if occupied:
                msg = f"您在{event['start_date']} {event['start_time']}到{event['end_time']}已有日程安排，请在前端重新创造新日程。"
                print("[WARN]", msg)
                speak_message(msg)

                page.close()

                # Wait for frontend to send new input
                latest_recognized_text = None
                print("[DEBUG] Waiting for frontend input...")
        
                while latest_recognized_text is None:
                    time.sleep(1)  # wait until frontend sends new text

                # Now we have valid input
                event = parse_event(latest_recognized_text)
                print("[DEBUG] New event data:", event)

                # Continue loop to check if new slot is free
                    
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

                print("date is: ", event["start_date"])

                page.get_by_label("Start date").click()
                # Suppose event["date"] = "2025-12-31"
                date_obj = datetime.strptime(event["start_date"], "%Y-%m-%d")
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
                page.get_by_role("option", name=start_time, exact=True).click()

                end_time_input = page.get_by_role("combobox", name="End time")
                end_time_input.click()
                end_time = round_up_24h_to_next_30mins(event["end_time"])
                
                print(event["end_time"])
                print(end_time)
                option_locator = page.get_by_role("option", name=end_time)

                try:
                    option_locator.click()
                except:
                # 找不到就往上滚动找下一个可选时间
                    all_options = page.get_by_label("End date").click()
                    count = all_options.count()
                    chosen = False
                    for i in range(count):
                        text = all_options.nth(i).inner_text().strip()
                    if text > end_time:  # 向上取整选择
                        all_options.nth(i).click()
                        chosen = True
                        break
                    if not chosen:
                        # 兜底：选择最后一个 option
                        all_options.nth(count-1).click()

                #page.get_by_label("End date").click()
                # Suppose event["date"] = "2025-12-31"
                # date_obj 是开始日期
                date_obj2 = datetime.strptime(event["end_date"], "%Y-%m-%d")
                # if event["start_time"] > event["end_time"]:
                #     end_date_obj = date_obj2 + timedelta(days=1)  # 增加一天
                # else:
                #     end_date_obj = date_obj2

                date_str2 = date_obj2.strftime("%Y%m%d")  

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

                #page.get_by_role("gridcell", name="31").click()
                # select the td representing the date
                #day_cell2 = page.locator(f'td[data-date="{date_str2}"]:not([data-dragsource-type])')

                # wait until visible, scroll if needed
                #day_cell2.wait_for(state="visible")
                #day_cell2.scroll_into_view_if_needed()

                # click it
                #day_cell2.click()

                page.get_by_role("gridcell", name=f"{date_obj2.day}, {date_obj2.strftime('%A')}").click()

                #page.get_by_role("gridcell", name=day_str2).filter(has_text=month_name).click()
                print("day selected")

                page.locator('button:has-text("Save")').first.click()
                break


