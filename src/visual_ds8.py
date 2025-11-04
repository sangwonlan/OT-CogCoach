# DeepStream 8.0 (Python) 상에서 카메라 프레임을 받아
# 중앙 박스의 "빨간색 비율"이 임계값을 넘으면 성공으로 기록합니다.
# base: deepstream-imagedata-multistream 샘플의 이미지 추출 패턴

import os, time, csv, numpy as np, cv2
from pathlib import Path
from gi.repository import Gst, GLib
import pyds  # DeepStream Python 바인딩

LOG_DIR = Path("logs"); LOG_DIR.mkdir(parents=True, exist_ok=True)
CSV_PATH = LOG_DIR / "visual.csv"

def _save_csv(success: bool, rt_ms: int | None):
    exists = CSV_PATH.exists()
    with CSV_PATH.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["datetime", "task", "success", "rt_ms"])
        w.writerow([time.strftime("%F %T"), "red_to_center", int(success), rt_ms if rt_ms is not None else -1])

def _camera_src():
    # USB 카메라 우선, 없으면 CSI 카메라 사용
    if os.path.exists("/dev/video0"):
        src = Gst.ElementFactory.make("v4l2src", "src")
        src.set_property("device", "/dev/video0")
        return src, "video/x-raw, width=1280, height=720, framerate=30/1"
    else:
        return Gst.ElementFactory.make("nvarguscamerasrc", "src"), "video/x-raw(memory:NVMM), width=1280, height=720, framerate=30/1, format=NV12"

def _build_pipeline():
    pipeline = Gst.Pipeline.new("otcog-ds8")
    src, caps_str = _camera_src()
    capsfilter = Gst.ElementFactory.make("capsfilter", "caps")
    capsfilter.set_property("caps", Gst.Caps.from_string(caps_str))

    # DeepStream 표준: nvstreammux(batch) → nvvideoconvert → (선택) nvdsosd → appsink
    conv0 = Gst.ElementFactory.make("nvvideoconvert", "conv0")
    mux = Gst.ElementFactory.make("nvstreammux", "mux")
    mux.set_property("batch-size", 1)
    mux.set_property("width", 1280)
    mux.set_property("height", 720)
    mux.set_property("live-source", 1)

    # src → conv0 → mux.sink_0
    # conv1에서 RGBA로 변환해 CPU 접근
    queue0 = Gst.ElementFactory.make("queue", "q0")
    conv1 = Gst.ElementFactory.make("nvvideoconvert", "conv1")
    caps_rgba = Gst.ElementFactory.make("capsfilter", "caps_rgba")
    caps_rgba.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), format=RGBA"))

    # 시각화가 필요하면 nvdsosd 추가 가능(여기서는 CPU로 가져와 OpenCV로 표시하지 않고 값만 측정)
    sink = Gst.ElementFactory.make("appsink", "sink")
    sink.set_property("emit-signals", True)
    sink.set_property("max-buffers", 1)
    sink.set_property("drop", True)
    sink.set_property("sync", False)

    for e in [src, capsfilter, conv0, queue0]:
        pipeline.add(e)
    pipeline.add(mux); pipeline.add(conv1); pipeline.add(caps_rgba); pipeline.add(sink)

    # src → caps → conv0 → queue0 → mux.sink_0
    src.link(capsfilter); capsfilter.link(conv0); conv0.link(queue0)
    sinkpad = mux.get_request_pad("sink_0")
    srcpad = queue0.get_static_pad("src")
    srcpad.link(sinkpad)

    # mux → conv1 → caps_rgba → appsink
    mux.link(conv1); conv1.link(caps_rgba); caps_rgba.link(sink)

    return pipeline, sink

def run_visual_task(threshold: float = 0.20, timeout_sec: int = 30):
    Gst.init(None)
    pipeline, appsink = _build_pipeline()

    result = {"success": False, "rt_ms": None, "start": time.time()}

    def on_new_sample(sink):
        sample = sink.emit("pull-sample")
        if sample is None:
            return Gst.FlowReturn.ERROR
        buf = sample.get_buffer()
        caps = sample.get_caps()
        s = caps.get_structure(0)
        width = s.get_value("width"); height = s.get_value("height")

        # NvBufSurface → numpy
        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(buf))
        # 배치 1 기준
        surf = pyds.get_nvds_buf_surface(hash(buf), 0)
        frame = np.array(surf, copy=True, order="C").reshape(height, width, 4)  # RGBA
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)

        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, (0, 100, 100), (10, 255, 255))
        m2 = cv2.inRange(hsv, (160, 100, 100), (179, 255, 255))
        mask = cv2.bitwise_or(m1, m2)

        h, w = mask.shape
        cx0, cx1 = int(w * 0.4), int(w * 0.6)
        cy0, cy1 = int(h * 0.4), int(h * 0.6)
        ratio = mask[cy0:cy1, cx0:cx1].mean() / 255.0

        if ratio > threshold and not result["success"]:
            result["success"] = True
            result["rt_ms"] = int((time.time() - result["start"]) * 1000)
            GLib.idle_add(stop_pipeline)
        return Gst.FlowReturn.OK

    def on_timeout():
        GLib.idle_add(stop_pipeline)
        return False

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
    GLib.timeout_add_seconds(timeout_sec, on_timeout)

    print("[DeepStream] 빨간 물체를 중앙(초록 박스 가정)으로 가져오세요…")
    try:
        loop.run()
    except KeyboardInterrupt:
        stop_pipeline()

    _save_csv(result["success"], result["rt_ms"])
    print(f"[결과] 성공={result['success']}, 반응시간(ms)={result['rt_ms']}")
