# src/visual_ds.py
# DeepStream(GStreamer + NVIDIA 요소) 파이프라인을 사용해
# 카메라 프레임을 appsink로 받아 중앙 박스의 "빨간색 비율"을 계산합니다.

import os, time, csv, numpy as np, cv2
from pathlib import Path
from gi.repository import Gst, GLib

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
CSV_PATH = LOG_DIR / "visual.csv"

def _save_csv(success: bool, rt_ms: int | None):
    exists = CSV_PATH.exists()
    with CSV_PATH.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["datetime", "task", "success", "rt_ms"])
        w.writerow([time.strftime("%F %T"), "red_to_center", int(success), rt_ms if rt_ms is not None else -1])

def _build_pipeline():
    """
    USB 카메라가 일반적이므로 우선 v4l2src를 시도하고,
    없으면 CSI 카메라(nvarguscamerasrc) 파이프라인을 구성합니다.
    """
    if os.path.exists("/dev/video0"):
        # USB 카메라
        return (
            "v4l2src device=/dev/video0 ! "
            "video/x-raw, width=1280, height=720, framerate=30/1 ! "
            "nvvidconv ! video/x-raw, format=BGR ! "
            "appsink name=sink emit-signals=true max-buffers=1 drop=true"
        )
    else:
        # CSI 카메라 (Jetson)
        return (
            "nvarguscamerasrc ! "
            "video/x-raw(memory:NVMM), width=1280, height=720, framerate=30/1, format=NV12 ! "
            "nvvidconv ! video/x-raw, format=BGR ! "
            "appsink name=sink emit-signals=true max-buffers=1 drop=true"
        )

def run_visual_task(threshold: float = 0.20, timeout_sec: int = 30):
    """
    threshold: 중앙 박스 내 빨간색 비율 임계값(0.15~0.30 권장)
    timeout_sec: 제한 시간 내 성공 못하면 종료
    """
    # DeepStream(GStreamer) 초기화
    Gst.init(None)
    pipeline_str = _build_pipeline()
    pipeline = Gst.parse_launch(pipeline_str)
    appsink = pipeline.get_by_name("sink")

    result = {"success": False, "rt_ms": None, "start": time.time()}

    def on_new_sample(sink):
        sample = sink.emit("pull-sample")
        if sample is None:
            return Gst.FlowReturn.ERROR

        buf = sample.get_buffer()
        caps = sample.get_caps()
        s = caps.get_structure(0)
        width = s.get_value("width")
        height = s.get_value("height")

        ok, mapinfo = buf.map(Gst.MapFlags.READ)
        if not ok:
            return Gst.FlowReturn.ERROR

        try:
            frame = np.frombuffer(mapinfo.data, dtype=np.uint8)
            frame = frame.reshape((height, width, 3))  # BGR
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # 빨간색 두 영역(저 H + 고 H)
            m1 = cv2.inRange(hsv, (0, 100, 100), (10, 255, 255))
            m2 = cv2.inRange(hsv, (160, 100, 100), (179, 255, 255))
            mask = cv2.bitwise_or(m1, m2)

            h, w = mask.shape
            cx0, cx1 = int(w * 0.4), int(w * 0.6)
            cy0, cy1 = int(h * 0.4), int(h * 0.6)
            center = mask[cy0:cy1, cx0:cx1]
            ratio = center.mean() / 255.0

            if ratio > threshold and not result["success"]:
                result["success"] = True
                result["rt_ms"] = int((time.time() - result["start"]) * 1000)
                # 파이프라인 종료
                GLib.idle_add(stop_pipeline)

        finally:
            buf.unmap(mapinfo)

        return Gst.FlowReturn.OK

    def on_timeout():
        # 제한 시간 초과 → 종료
        GLib.idle_add(stop_pipeline)
        return False  # 타이머 1회성

    def stop_pipeline():
        try:
            pipeline.set_state(Gst.State.NULL)
        except Exception:
            pass
        loop.quit()
        return False

    appsink.connect("new-sample", on_new_sample)
    pipeline.set_state(Gst.State.PLAYING)

    loop = GLib.MainLoop()
    # 타임아웃 등록
    GLib.timeout_add_seconds(timeout_sec, on_timeout)

    print("[안내] DeepStream 파이프라인 실행: 빨간 물체를 화면 중앙으로 가져오세요.")
    try:
        loop.run()
    except KeyboardInterrupt:
        stop_pipeline()

    _save_csv(result["success"], result["rt_ms"])
    print(f"[결과] 성공={result['success']}, 반응시간(ms)={result['rt_ms']}")
