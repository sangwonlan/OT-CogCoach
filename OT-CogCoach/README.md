# OT-CogCoach (Terminal Only)

작업치료(OT) 인지 과제 2종을 터미널에서 실행하는 최소 예제입니다.

- **언어 유창성(60초)**: 녹음 → `faster-whisper` 전사 → (선택) 로컬 LLM(Ollama)로 자동 채점 → CSV 저장  
- **시각 탐색**: 카메라 프레임에서 빨간색을 중앙 박스에 위치시키면 성공 → 반응시간/성공여부 CSV 저장

> 연구·교육용 프로토타입입니다. 의료적 진단/치료 결정을 단독으로 대체하지 않습니다.

## 1) 설치
```bash
python -m venv .venv
# Windows
.\.venv\Scriptsctivate
# Linux / macOS
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2) 실행
### 시각 탐색
```bash
python main.py --task visual
```
### 언어 유창성(예: 60초, 동물 카테고리)
```bash
python main.py --task fluency --category "동물" --duration 60
```
- 결과: `logs/visual.csv`, `logs/fluency.csv` / 음성 파일: `logs/fluency.wav`

> (선택) **LLM 채점**: 로컬에서 Ollama 실행 후 `ollama pull llama3.1`  
> Ollama가 없으면 자동으로 **임시 채점**을 사용합니다.

## 3) GitHub 업로드(요약)
```bash
git init && git add .
git commit -m "init: OT-CogCoach (fluency + visual)"
git branch -M main
git remote add origin https://github.com/<YOUR_ID>/OT-CogCoach.git
git push -u origin main
```
