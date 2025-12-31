# 语音驱动日程助手

## 功能
- 语音输入日程
- 自动解析时间
- 通过浏览器自动化添加 Google 日历事件
- 不使用 Google Calendar API

## 技术
- FastAPI
- Playwright
- Web Speech API

## 使用步骤
1. 启动后端
2. 首次运行手动登录 Google
3. 打开前端页面
4. 点击按钮说话

## Setup
```bash
git clone <repo-url>
cd <repo-name>

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

cd Voice_Calendar_Assistance/backend
pip install -r requirements.txt
playwright install

uvicorn main:app --reload
python -m http.server 8080

## Installing PyAudio

### Windows
PyAudio may require a pre-built wheel. You can install it with:

1. Download the correct wheel for your Python version:  
   https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
2. Install with pip:
   pip install path\to\PyAudio‑<version>.whl 

