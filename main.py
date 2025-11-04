import argparse
from src.fluency import run_fluency
from src.visual_ds8 import run_visual_task  # DeepStream 백엔드

def parse_args():
    p = argparse.ArgumentParser(description="OT-CogCoach (DeepStream 8.0)")
    p.add_argument("--task", choices=["fluency", "visual"], required=True)
    p.add_argument("--category", default="동물")
    p.add_argument("--duration", type=int, default=60)
    p.add_argument("--threshold", type=float, default=0.20)
    p.add_argument("--timeout", type=int, default=30)
    return p.parse_args()

def main():
    args = parse_args()
    if args.task == "fluency":
        run_fluency(category=args.category, duration=args.duration)
    else:
        run_visual_task(threshold=args.threshold, timeout_sec=args.timeout)

if __name__ == "__main__":
    main()
