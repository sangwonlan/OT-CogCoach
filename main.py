# main.py
import argparse
from src.fluency import run_fluency
from src.visual_ds import run_visual_task  # ← DeepStream 버전 사용

def parse_args():
    p = argparse.ArgumentParser(description="OT-CogCoach (DeepStream)")
    p.add_argument("--task", choices=["fluency", "visual"], required=True,
                   help="실행할 과제 선택")
    p.add_argument("--category", default="동물",
                   help="언어 유창성 카테고리 (예: 동물/과일/교통수단/ㄷ으로 시작)")
    p.add_argument("--duration", type=int, default=60,
                   help="언어 유창성 녹음 시간(초)")
    p.add_argument("--threshold", type=float, default=0.20,
                   help="시각 탐색 중앙 박스 내 빨강 비율 임계값(0.15~0.30 권장)")
    p.add_argument("--timeout", type=int, default=30,
                   help="시각 탐색 제한 시간(초)")
    return p.parse_args()

def main():
    args = parse_args()
    if args.task == "fluency":
        run_fluency(category=args.category, duration=args.duration)
    else:
        run_visual_task(threshold=args.threshold, timeout_sec=args.timeout)

if __name__ == "__main__":
    main()
