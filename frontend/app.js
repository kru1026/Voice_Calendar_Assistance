const btn = document.getElementById("recordBtn");
const result = document.getElementById("result");

const greeting = "您好，我是您的日程助手，你要记录什么日程？";

console.log("[DEBUG] Script loaded");

btn.onclick = () => {
  console.log("[DEBUG] Record button clicked");
  btn.disabled = true;
  console.log("[DEBUG] Button locked, starting speakThenListen");

  speakThenListen();
};

function speakThenListen() {
  console.log("[DEBUG] speakThenListen()");

  const utterance = new SpeechSynthesisUtterance(greeting);
  utterance.lang = "zh-CN";

    utterance.onend = () => {
      console.log("[DEBUG] Greeting speech ended");
      startRecognition();
    };

    speechSynthesis.speak(utterance);
  }

function startRecognition() {
  console.log("[DEBUG] startRecognition()");

  const recognition = new webkitSpeechRecognition();
  recognition.lang = "zh-CN";
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.start();
  console.log("[DEBUG] Speech recognition started");

  recognition.onresult = async (e) => {
    console.log("[DEBUG] Recognition result event:", e);

    recognition.stop();
    console.log("[DEBUG] Recognition stopped");

    const text = e.results[0][0].transcript;
    console.log("[DEBUG] Recognized text:", text);

    result.innerText = "识别内容：" + text;

    result.appendChild(document.createElement("br"));
    result.appendChild(document.createElement("br"));

    const playBtn = document.createElement("button");
    playBtn.innerText = "语音播放";
    playBtn.onclick = () => {
      console.log("[DEBUG] Play button clicked");
      speakText(text);
    };
    result.appendChild(playBtn);

    result.appendChild(document.createElement("br"));
    result.appendChild(document.createElement("br"));

    const actionBtn = document.createElement("button");
    actionBtn.innerText = "重新创建";
    actionBtn.onclick = () => {
      console.log("[DEBUG] Reload button clicked");
      location.reload();
    };
    result.appendChild(actionBtn);

    console.log("[DEBUG] Sending text to backend:", text);

    try {
      const resp = await fetch("http://127.0.0.1:8000/speech", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
      });
      console.log("[DEBUG] Backend response status:", resp.status);
    } catch (err) {
      console.error("[ERROR] Backend request failed:", err);
    }
  };

  recognition.onerror = (e) => {
    recognition.stop();
    console.error("[ERROR] Speech recognition error:", e);
    console.log("[DEBUG] busy unlocked after error");
  };
}

function speakText(text) {
  console.log("[DEBUG] speakText()", text);

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "zh-CN";

  function setVoice() {
    const voices = speechSynthesis.getVoices();
    const zhVoice = voices.find(v => v.lang.startsWith("zh"));
    if (zhVoice) {
      utterance.voice = zhVoice;
      console.log("[DEBUG] speakText using voice:", zhVoice.name);
    } else {
      console.log("[WARN] speakText no zh voice found");
    }
  }

  if (speechSynthesis.getVoices().length === 0) {
    console.log("[DEBUG] Voices not loaded yet, waiting...");
    speechSynthesis.onvoiceschanged = () => {
      console.log("[DEBUG] Voices loaded");
      setVoice();
      speechSynthesis.speak(utterance);
    };
  } else {
    setVoice();
    speechSynthesis.speak(utterance);
  }
}
