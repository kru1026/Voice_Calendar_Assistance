from playwright.sync_api import sync_playwright
import time

def add_event_to_calendar(event):
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="chrome_data",
            headless=False,
            channel="chrome"
        )

        page = browser.new_page()
        page.goto("https://calendar.google.com")
        time.sleep(5)

        # 点击“创建”
        page.click("text=创建")
        time.sleep(2)

        # 填写标题
        page.fill('input[aria-label="添加标题"]', event["title"])

        # 填写时间
        page.fill('input[aria-label="开始时间"]', event["start_time"])
        page.fill('input[aria-label="结束时间"]', event["end_time"])

        # 保存
        page.click("text=保存")
        time.sleep(2)

        browser.close()
