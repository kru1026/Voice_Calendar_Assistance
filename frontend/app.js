const btn = document.getElementById("recordBtn");
const result = document.getElementById("result");

btn.onclick = () => {
  const recognition = new webkitSpeechRecognition();
  recognition.lang = "zh-CN";
  recognition.start();

  recognition.onresult = async (e) => {
    const text = e.results[0][0].transcript;
    result.innerText = "识别内容：" + text;

    await fetch("http://127.0.0.1:8000/speech", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
  };
};
