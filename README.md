# OT-CogCoach (Terminal Only)

작업치료(OT) 인지 과제 2종을 터미널에서 실행하는 최소 예제입니다.

- **언어 유창성(60초)**: 녹음 → `faster-whisper` 전사 → (선택) 로컬 LLM(Ollama) 자동 채점 → CSV 저장  
- **시각 탐색**: 카메라 프레임에서 빨간색을 중앙 박스에 위치시키면 성공 → 반응시간/성공여부 CSV 저장

> 연구·교육용 프로토타입입니다. 의료적 진단/치료 결정을 단독으로 대체하지 않습니다.

## 설치
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

##시작 만 탐색하게 하는거
##python main.py --task visual
##언어 유창성 체크
##python main.py --task fluency --category "동물" --duration 60

---

## (2) `requirements.txt`
##**Add file → Create new file**  
##**Name**: `requirements.txt` → 내용 붙여넣기 → Commit
##```txt
##numpy==1.26.4
##opencv-python>=4.8,<5
##faster-whisper>=1.0
##requests>=2.31
##sounddevice>=0.4.6
##soundfile>=0.12.1
