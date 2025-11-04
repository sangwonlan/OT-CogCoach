import os, time, json, requests, platform
from pathlib import Path
from typing import Dict, Any
from faster_whisper import WhisperModel

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
WAV_PATH = LOG_DIR / "fluency.wav"
CSV_PATH = LOG_DIR / "fluency.csv"

def _record_windows(duration: int):
    import sounddevice as sd, soundfile as sf
    fs = 16000
    print(f"[안내] {duration}초 녹음 시작 (Windows)")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="int16")
    sd.wait()
    sf.write(str(WAV_PATH), audio, fs)

def _record_posix(duration: int):
    try:
        import sounddevice as sd, soundfile as sf
        fs = 16000
        print(f"[안내] {duration}초 녹음 시작 (sounddevice)")
        audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="int16")
        sd.wait()
        sf.write(str(WAV_PATH), audio, fs)
    except Exception:
        import subprocess
        print(f"[안내] {duration}초 녹음 시작 (arecord 대체)")
        subprocess.run(["arecord", "-d", str(duration), "-f", "cd", "-t", "wav", str(WAV_PATH)], check=True)

def _transcribe() -> str:
    model = WhisperModel("base", device="auto", compute_type="int8")
    segments, _ = model.transcribe(str(WAV_PATH), vad_filter=True, language="ko")
    return " ".join(s.text.strip() for s in segments).strip()

def _score_with_llm(text: str, duration: int, category: str) -> Dict[str, Any]:
    prompt = f"""아래 한국어 텍스트는 {duration}초 동안 말한 단어들입니다.
카테고리={category}
텍스트="{text}"
JSON만 출력: {{"unique":고유단어수,"dup":중복무관수,"score":고유-중복,"list":[고유단어들]}}"""
    r = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3.1", "prompt": prompt, "stream": False},
        timeout=180,
    )
    return json.loads(r.json()["response"])

def _save_csv(row):
    exists = CSV_PATH.exists()
    with CSV_PATH.open("a", encoding="utf-8") as f:
        if not exists:
            f.write("datetime,category,unique,dup,score,text\n")
        f.write(",".join([
            time.strftime("%F %T"),
            row.get("category",""),
            str(row.get("unique","")),
            str(row.get("dup","")),
            str(row.get("score","")),
            '"' + row.get("text","").replace('"','""') + '"'
        ]) + "\n")

def run_fluency(category: str = "동물", duration: int = 60):
    print(f"[안내] {category} 이름을 {duration}초 동안 말해보세요!")
    if platform.system() == "Windows":
        _record_windows(duration)
    else:
        _record_posix(duration)

    text = _transcribe()

    try:
        data = _score_with_llm(text, duration, category)
    except Exception as e:
        words = [w for w in text.split() if w]
        uniq = len(set(words)); dup = len(words) - uniq
        data = {"unique": uniq, "dup": dup, "score": uniq - dup, "list": list(set(words))}
        print("[안내] LLM 미사용/실패 → 임시 채점으로 진행:", e)

    row = {"category": category, "text": text, **data}
    _save_csv(row)
    print(f"[결과] 고유:{data['unique']}  중복:{data['dup']}  점수:{data['score']}")
