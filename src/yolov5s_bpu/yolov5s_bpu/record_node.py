#!/usr/bin/env python3
"""Aurora930 RGB 录制 + Web 预览 — Ctrl+C 停止"""

import os, time, signal
import numpy as np, cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage


class RecordNode(Node):
    def __init__(self):
        super().__init__('record_node')
        self.declare_parameter('output_dir', 'resource')
        self.declare_parameter('fps', 15.0)

        self.out_dir = self.get_parameter('output_dir').value
        # 使用源码目录 src/yolov5s_bpu/resource（不被 colcon build 清理）
        self.out_dir = '/root/dev_ws/src/yolov5s_bpu/resource'
        self.fps = self.get_parameter('fps').value
        os.makedirs(self.out_dir, exist_ok=True)

        path = os.path.join(self.out_dir, f'aurora_{time.strftime("%Y%m%d_%H%M%S")}.mp4')
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(path, fourcc, self.fps, (640, 400))
        if not self.writer.isOpened():
            raise RuntimeError(f'Cannot open: {path}')

        self.frame_count = 0
        self.path = path
        self._sub = self.create_subscription(Image, '/aurora/rgb/image_raw', self._cb, 10)
        self._pub = self.create_publisher(CompressedImage, '/image_jpeg', 10)
        self.get_logger().info(f'● REC {path}  (Ctrl+C to stop)')

    def _cb(self, msg):
        try:
            bgr = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)

            disp = bgr.copy()
            cv2.circle(disp, (20, 20), 10, (0, 0, 255), -1)
            cv2.putText(disp, f'REC {self.frame_count}', (40, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            ok, jpg = cv2.imencode('.jpg', disp, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                self._pub.publish(CompressedImage(header=msg.header, format='jpeg', data=jpg.tobytes()))

            self.writer.write(bgr)
            self.frame_count += 1
        except Exception as e:
            self.get_logger().error(f'{e}')

    def destroy_node(self):
        if self.writer:
            self.writer.release()
        self.get_logger().info(f'■ Saved: {self.path} ({self.frame_count} frames)')
        super().destroy_node()


def main():
    rclpy.init()
    node = RecordNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
