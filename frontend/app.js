const btn = document.getElementById("recordBtn");
const result = document.getElementById("result");

const greeting = "您好，我是您的日程助手，你要记录什么日程？";

// 状态锁
let busy = false;

btn.onclick = () => {
  if (busy) return; // 播报/识别期间直接忽略
  busy = true;
  btn.disabled = true;
  speakThenListen();
};

function speakThenListen() {
  const utterance = new SpeechSynthesisUtterance(greeting);
  utterance.lang = "zh-CN";

  // 可选：选中文声音
  const voices = speechSynthesis.getVoices();
  const zhVoice = voices.find(v => v.lang.startsWith("zh"));
  if (zhVoice) utterance.voice = zhVoice;

  utterance.onend = () => {
    startRecognition();
  };

  speechSynthesis.speak(utterance);
}

function startRecognition() {
  const recognition = new webkitSpeechRecognition();
  recognition.lang = "zh-CN";
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.start();

  recognition.onresult = async (e) => {
    recognition.stop();

    const text = e.results[0][0].transcript;
    result.innerText = "识别内容：" + text;

    // 第一个换行
    result.appendChild(document.createElement("br"));

    // 第二个换行
    result.appendChild(document.createElement("br"));

    const playBtn = document.createElement("button");
    playBtn.innerText = "语音播放";
    playBtn.onclick = () => {
      speakText(text);
    };

    result.appendChild(playBtn);

    // 第一个换行
    result.appendChild(document.createElement("br"));

    // 第二个换行
    result.appendChild(document.createElement("br"));
    
    // 然后再添加按钮或其他内容
    const actionBtn = document.createElement("button");
    actionBtn.innerText = "重新创建";
    actionBtn.onclick = () => {
    location.reload();
    };
    result.appendChild(actionBtn);

    await fetch("http://127.0.0.1:8000/speech", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });

    // 解锁按钮
    busy = false;
    btn.disabled = false;
  };

  recognition.onerror = (e) => {
    recognition.stop();
    console.error("语音识别错误", e);
    busy = false;
    btn.disabled = false;
  };
}

function speakText(text) {
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "zh-CN";

  // Helper to set voice
  function setVoice() {
    const voices = speechSynthesis.getVoices();
    const zhVoice = voices.find(v => v.lang.startsWith("zh"));
    if (zhVoice) utterance.voice = zhVoice;
  }

  if (speechSynthesis.getVoices().length === 0) {
    // Voices not loaded yet
    speechSynthesis.onvoiceschanged = () => {
      setVoice();
      speechSynthesis.speak(utterance);
    };
  } else {
    setVoice();
    speechSynthesis.speak(utterance);
  }
}
