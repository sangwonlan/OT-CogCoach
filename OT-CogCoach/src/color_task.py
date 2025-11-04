import time, csv
from pathlib import Path
import cv2

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
CSV_PATH = LOG_DIR / "visual.csv"

def _save_csv(success: bool, rt_ms: int | None):
    exists = CSV_PATH.exists()
    with CSV_PATH.open("a", encoding="utf-8") as f:
        if not exists:
            f.write("datetime,task,success,rt_ms\n")
        f.write(",".join([
            time.strftime("%F %T"),
            "red_to_center",
            "1" if success else "0",
            str(rt_ms if rt_ms is not None else -1)
        ]) + "\n")

def run_visual_task(threshold: float = 0.20):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("카메라를 열 수 없습니다. 다른 인덱스(1,2)로 시도해 보세요.")

    start = time.time(); success = False; rt_ms = None
    print("[안내] 빨간 물체를 화면 중앙으로 가져오세요. (ESC 종료)")

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, (0, 100, 100), (10, 255, 255))
        m2 = cv2.inRange(hsv, (160, 100, 100), (179, 255, 255))
        mask = cv2.bitwise_or(m1, m2)

        h, w = mask.shape
        cx0, cx1 = int(w * 0.4), int(w * 0.6)
        cy0, cy1 = int(h * 0.4), int(h * 0.6)
        center = mask[cy0:cy1, cx0:cx1]
        ratio = center.mean() / 255.0

        cv2.rectangle(frame, (cx0, cy0), (cx1, cy1), (0, 255, 0), 2)
        cv2.putText(frame, f"center-red:{ratio:.2f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        if ratio > threshold:
            success = True
            rt_ms = int((time.time() - start) * 1000)
            cv2.putText(frame, "SUCCESS", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 3)
            cv2.imshow("task", frame); cv2.waitKey(700); break

        cv2.imshow("task", frame)
        if cv2.waitKey(1) == 27:
            break

    cap.release(); cv2.destroyAllWindows()
    _save_csv(success, rt_ms)
    print(f"[결과] 성공={success}, 반응시간(ms)={rt_ms}")
