#!/usr/bin/env python3
"""YOLOv5 BPU + 深度标注 — 纯 Python 后处理，兼容任意类数模型"""

import json, time, threading, os
import numpy as np, cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage
from ai_msgs.msg import PerceptionTargets, Target, Roi, Perf
from detection_interfaces.msg import DetectionResult, DetectionArray
from std_msgs.msg import Header

try:
    from hobot_dnn import pyeasy_dnn as dnn
except ImportError:
    from hobot_dnn_rdkx5 import pyeasy_dnn as dnn


def sig(x):
    return 0.5 * (1.0 + np.tanh(x * 0.5))


class YOLOv5Decoder:
    """纯 Python YOLOv5 解码 + NMS"""
    def __init__(self, nc=31, conf=0.4, nms_iou=0.5, nms_topk=500, input_w=640, input_h=640,
                 anchors=None, strides=None):
        self.nc, self.conf, self.nms_iou, self.nms_topk = nc, conf, nms_iou, nms_topk
        self.input_w, self.input_h = input_w, input_h
        if strides is None: strides = [8, 16, 32]
        if anchors is None:
            anchors = [[[10,13],[16,30],[33,23]], [[30,61],[62,45],[59,119]], [[116,90],[156,198],[373,326]]]
        self._grids = []
        for s, anc in zip(strides, anchors):
            H, W = input_h // s, input_w // s
            a = np.array(anc, dtype=np.float32).reshape(1, 1, 3, 2)
            self._grids.append({
                'gy': np.arange(H, dtype=np.float32)[:, None, None, None],
                'gx': np.arange(W, dtype=np.float32)[None, :, None, None],
                'a': a, 's': s, 'H': H, 'W': W,
            })

    def __call__(self, outputs, img_h, img_w):
        sx, sy = img_w / self.input_w, img_h / self.input_h
        boxes_l, scores_l, cls_l = [], [], []

        for i, out in enumerate(outputs):
            g = self._grids[i]; H, W, s = g['H'], g['W'], g['s']
            total = H * W * 3
            buf = np.asarray(out.buffer)
            # 适配两种输出格式
            if buf.ndim == 5:  # (1, na, W, H, C) → (H, W, na, C)
                raw = buf[0].transpose(2, 3, 0, 1)  # → (H, W, na, C)
            else:              # NHWC: (1, H, W, na*C) → (H, W, na, C)
                raw = buf.reshape(H, W, 3, 5 + self.nc)

            # bbox+obj sigmoid
            head = sig(raw[..., :5])
            tx = head[..., 0:1] * 2.0 - 0.5; ty = head[..., 1:2] * 2.0 - 0.5
            tw = (head[..., 2:3] * 2.0) ** 2; th = (head[..., 3:4] * 2.0) ** 2
            obj = head[..., 4:5]

            xc = (tx + g['gx']) * s; yc = (ty + g['gy']) * s
            bw = tw * g['a'][..., 0:1]; bh = th * g['a'][..., 1:2]
            x1 = (xc - bw * 0.5).ravel(); y1 = (yc - bh * 0.5).ravel()
            x2 = (xc + bw * 0.5).ravel(); y2 = (yc + bh * 0.5).ravel()
            obj = obj.ravel()

            # 预过滤
            cls_rough = sig(raw[..., 5:].reshape(total, self.nc).max(axis=1))
            mask = (obj * cls_rough) > (self.conf * 0.5)
            if not mask.any(): continue

            # 完整类别 sigmoid
            cls_s = sig(raw[..., 5:].reshape(total, self.nc)[mask])
            scores = obj[mask] * cls_s.max(axis=1)
            final = scores > self.conf
            if not final.any(): continue

            idx = np.where(mask)[0][final]
            boxes_l.append(np.stack([
                np.clip(x1[idx] * sx, 0, img_w), np.clip(y1[idx] * sy, 0, img_h),
                np.clip(x2[idx] * sx, 0, img_w), np.clip(y2[idx] * sy, 0, img_h),
            ], axis=1))
            scores_l.append(scores[final])
            cls_l.append(cls_s[final].argmax(axis=1))

        if not boxes_l: return []
        boxes = np.concatenate(boxes_l); scores = np.concatenate(scores_l); classes = np.concatenate(cls_l)
        idx = cv2.dnn.NMSBoxes(boxes.tolist(), scores.tolist(), self.conf, self.nms_iou, top_k=self.nms_topk)
        if len(idx) == 0: return []
        idx = np.array(idx).ravel()
        return [{'bbox': boxes[i].tolist(), 'score': float(scores[i]), 'id': int(classes[i])} for i in idx]


class YOLOv5sBPUNode(Node):
    def __init__(self):
        super().__init__('yolov5s_bpu_node')
        self.declare_parameter('config_file', '/root/dev_ws/src/config/weaponconfig/yolov5sconfig.json')
        config_file = self.get_parameter('config_file').value

        # 加载 JSON 配置
        if not os.path.isabs(config_file):
            from ament_index_python import get_package_prefix
            pkg = get_package_prefix('yolov5s_bpu')
            config_file = os.path.join(pkg, 'lib', 'yolov5s_bpu', config_file)
        with open(config_file) as f:
            cfg = json.load(f)

        m = cfg['model_file']
        if not os.path.isabs(m):
            from ament_index_python import get_package_prefix
            m = os.path.join(get_package_prefix('yolov5s_bpu'), 'lib', 'yolov5s_bpu', m)
        self.nc = cfg.get('class_num', 31)
        conf = cfg.get('score_threshold', 0.4)
        nms = cfg.get('nms_threshold', 0.5)
        nms_top_k = cfg.get('nms_top_k', 500)
        anchors = cfg.get('anchors_table', None)
        strides_list = cfg.get('strides', None)

        # 类别名（从配置中的 cls_names_list 加载）
        cls_path = cfg.get('cls_names_list', 'config/redconfig/custom.list')
        if not os.path.isabs(cls_path):
            from ament_index_python import get_package_prefix
            pkg2 = get_package_prefix('yolov5s_bpu')
            cls_path = os.path.join(pkg2, 'lib', 'yolov5s_bpu', cls_path)
        with open(cls_path) as f:
            self.names = [l.strip() for l in f if l.strip()]
        self.get_logger().info(f'Config: {config_file}')
        self.get_logger().info(f'Model: {m} | classes={self.nc}')

        # 名称重映射
        self._remap = {'hand': 'lance', 'fist': 'hand', 'lance': 'fist'}

        # BPU
        self.models = dnn.load(m)
        props = self.models[0].inputs[0].properties
        self.mh, self.mw = (props.shape[2], props.shape[3]) if props.layout == 'NCHW' else (props.shape[1], props.shape[2])
        self.decoder = YOLOv5Decoder(nc=self.nc, conf=conf, nms_iou=nms, nms_topk=nms_top_k,
                                     input_w=self.mw, input_h=self.mh,
                                     anchors=anchors, strides=strides_list)
        self.get_logger().info(f'BPU ready: {self.mw}x{self.mh}')

        # 深度缓存
        self._dlock = threading.Lock(); self._depth = None
        self.create_subscription(Image, '/aurora/depth/image_raw', self._cb_depth, 10)
        self.create_subscription(Image, '/aurora/rgb/image_raw', self._cb_rgb, 10)
        self._pub_det = self.create_publisher(PerceptionTargets, 'hobot_dnn_detection', 10)
        self._pub_jpg = self.create_publisher(CompressedImage, '/image_jpeg', 10)
        self._pub_custom = self.create_publisher(DetectionArray, '/detections', 10)
        self.get_logger().info('=== Ready ===')

    def _cb_depth(self, msg):
        try:
            d = np.frombuffer(msg.data, dtype=np.uint16).reshape(msg.height, msg.width).copy()
            with self._dlock: self._depth = d
        except Exception: pass

    def _remap_name(self, name):
        return self._remap.get(name, name)

    def _depth_at(self, cx, cy, r=3):
        with self._dlock:
            d = self._depth
            if d is None: return 0
        h, w = d.shape
        px, py = int(cx * w), int(cy * h)
        roi = d[max(0, py - r):min(h, py + r + 1), max(0, px - r):min(w, px + r + 1)]
        v = roi[roi > 0]; return int(np.median(v)) if len(v) else 0

    def _cb_rgb(self, msg):
        t0 = time.time()
        try:
            bgr = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
            org_h, org_w = bgr.shape[:2]

            # JPEG 给 websocket
            ok, jpg = cv2.imencode('.jpg', bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                self._pub_jpg.publish(CompressedImage(header=msg.header, format='jpeg', data=jpg.tobytes()))

            # ── Letterbox: 保持宽高比，补灰边 → 模型输入尺寸 ──
            scale = min(self.mw / org_w, self.mh / org_h)
            new_w, new_h = int(org_w * scale), int(org_h * scale)
            pad_left = (self.mw - new_w) // 2
            pad_top = (self.mh - new_h) // 2
            resized = cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
            letterbox = cv2.copyMakeBorder(resized, pad_top, self.mh - new_h - pad_top,
                                          pad_left, self.mw - new_w - pad_left,
                                          borderType=cv2.BORDER_CONSTANT, value=(114, 114, 114))

            # BGR → NV12
            area = self.mh * self.mw
            yuv = cv2.cvtColor(letterbox, cv2.COLOR_BGR2YUV_I420).reshape(area * 3 // 2)
            nv12 = np.zeros_like(yuv); nv12[:area] = yuv[:area]
            uv = yuv[area:].reshape(2, area // 4); nv12[area:] = uv.transpose(1, 0).reshape(area // 2)

            # BPU + 解码（在模型 640×640 空间）
            outputs = self.models[0].forward(nv12)
            t1 = time.time()
            dets = self.decoder(outputs, self.mh, self.mw)
            t2 = time.time()
            # 修正 letterbox：去除 padding + 缩放到原始尺寸
            for d in dets:
                b = d['bbox']
                b[0] = (b[0] - pad_left) / scale
                b[1] = (b[1] - pad_top) / scale
                b[2] = (b[2] - pad_left) / scale
                b[3] = (b[3] - pad_top) / scale
                b[0] = max(0, min(org_w, b[0]))
                b[1] = max(0, min(org_h, b[1]))
                b[2] = max(0, min(org_w, b[2]))
                b[3] = max(0, min(org_h, b[3]))
            self.get_logger().info(f'[{len(dets)}] infer={(t1-t0)*1000:.0f}ms decode={(t2-t1)*1000:.0f}ms')

            # 发布
            msg2 = PerceptionTargets(header=msg.header, fps=-1)
            msg2.perfs = [Perf(type='yolov5s_bpu', time_ms_duration=(t2-t0)*1000)]
            for d in dets:
                b = d['bbox']
                cx, cy = (b[0]+b[2])/2.0/org_w, (b[1]+b[3])/2.0/org_h
                mm = self._depth_at(cx, cy)
                raw_name = self.names[d['id']] if 0 <= d['id'] < len(self.names) else '?'
                name = self._remap_name(raw_name)
                label = f'{name} {d["score"]:.2f} {mm}mm' if mm else f'{name} {d["score"]:.2f}'
                t = Target(type=label, track_id=0)
                roi = Roi(type=label, confidence=d['score'])
                roi.rect.x_offset, roi.rect.y_offset = int(b[0]), int(b[1])
                roi.rect.width, roi.rect.height = int(b[2]-b[0]), int(b[3]-b[1])
                t.rois = [roi]; msg2.targets.append(t)
            self._pub_det.publish(msg2)

            # 自定义消息 /detections
            carray = DetectionArray()
            carray.header.stamp = self.get_clock().now().to_msg()
            carray.header.frame_id = msg.header.frame_id
            for d in dets:
                b = d['bbox']
                r = DetectionResult()
                cls_id = d['id']
                r.name = self._remap_name(self.names[cls_id] if 0 <= cls_id < len(self.names) else '?')
                r.x1 = b[0] / org_w
                r.y1 = b[1] / org_h
                r.x2 = b[2] / org_w
                r.y2 = b[3] / org_h
                r.confidence = d['score']
                cx, cy = (b[0]+b[2])/2.0/org_w, (b[1]+b[3])/2.0/org_h
                r.depth_mm = float(self._depth_at(cx, cy))
                r.timestamp = self.get_clock().now().to_msg()
                carray.detections.append(r)
            self._pub_custom.publish(carray)
        except Exception as e:
            self.get_logger().error(f'{e}')

def main():
    rclpy.init(); rclpy.spin(YOLOv5sBPUNode())

if __name__ == '__main__':
    main()
