# RDK X5 — Aurora 930 深度相机 + BPU YOLOv5 检测系统

Horizon RDK X5 上的实时目标检测与深度标注系统，用于自主机器人感知。

## 开机自启动

已配置 systemd 服务，开机离线自动启动：

```bash
# 启停控制
systemctl start ros2-yolo      # 立即启动
systemctl stop ros2-yolo       # 停止
systemctl status ros2-yolo     # 查看状态
systemctl enable ros2-yolo     # 开机自启（已启用）
systemctl disable ros2-yolo    # 取消开机自启

# 查看日志
journalctl -u ros2-yolo -f     # 实时
tail -f ~/dev_ws/log/auto_start.log        # stdout
tail -f ~/dev_ws/log/auto_start_error.log  # stderr
```

服务文件：`/etc/systemd/system/ros2-yolo.service`，崩溃后 10 秒自动重启。

ROS2 节点（可用 `ros2 node list` 查看）：`/yolov5s_bpu`、`/websocket`、`/aurora/aurora930_node`

## 硬件架构

```
RDK X5                               另一台设备 (192.168.127.1)
├─ Aurora 930 (USB)                  ├─ chrony NTP 客户端
├─ BPU YOLOv5 推理                   └─ ROS2 节点订阅 /detections
├─ chrony NTP 主时钟 (192.168.127.10)
└─ WebSocket 可视化 (:8000)
        │
  有线网线直连 (eth0, 192.168.127.x)
```

## 功能包

| 包 | 说明 |
|------|------|
| `detection_interfaces` | 自定义 ROS2 消息（DetectionResult / DetectionArray） |
| `yolov5s_bpu` | BPU 推理 + 深度标注 + Web 可视化 |
| `deptrum-ros-driver` | Aurora 930 相机驱动（第三方） |

## 编译

```bash
cd ~/dev_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select detection_interfaces yolov5s_bpu
source ~/dev_ws/install/setup.bash
```

## 一键启动

```bash
ros2 launch yolov5s_bpu yolov5s_bpu.launch.py
```

浏览器 `http://192.168.127.10:8000`

## 话题总览

| 话题 | 类型 | 频率 | 方向 | 说明 |
|------|------|------|------|------|
| `/aurora/rgb/image_raw` | Image(BGR8) | ~15Hz | 相机→BPU | 彩色 640×400 |
| `/aurora/depth/image_raw` | Image(16UC1) | ~15Hz | 相机→BPU | 深度 mm |
| `/image_jpeg` | CompressedImage | ~15Hz | BPU→Web | Web 显示 |
| `/hobot_dnn_detection` | PerceptionTargets | ~15Hz | BPU→Web | 检测结果 |
| `/detections` | DetectionArray | ~15Hz | BPU→另一台 | 归一化检测+深度 |

## 相机

Aurora 930, 固件 v1.7.2, USB 连接。

| 分辨率模式 | RGB | 深度 |
|-----------|------|------|
| 0 | 320×200 | 320×200 |
| 1 | 480×300 | 480×300 |
| 2 (当前) | 640×400 | 640×400 |

帧率 ~15fps。启动时使用 `resolution_mode_index:=2`。

## 检测输出 `/detections` 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 物品名称 |
| `x1,y1,x2,y2` | float32 | 归一化角点 (0~1) |
| `confidence` | float32 | 置信度 |
| `depth_mm` | float32 | bbox 中心深度 (mm) |
| `timestamp` | Time | 检测时间戳 |

## 模型配置

存放于 `/root/dev_ws/src/config/`：

| 配置 | 类数 | 标签 |
|------|------|------|
| `weaponconfig` | 3 | lance, fist, hand |
| `redconfig` | 31 | R_ / RT_ / RF_ 系列 |
| `blueconfig` | 31 | B_ / BT_ / BF_ 系列 |

切换：`config_file:=/root/dev_ws/src/config/<name>/yolov5sconfig.json`

## 时间同步

- 主时钟：本机 chrony (192.168.127.10, Stratum 10)
- 客户端：另一台设备 → `server 192.168.127.10 iburst`
- 均 `systemctl enable chrony` 开机自启

## 录制

```bash
ros2 launch yolov5s_bpu record.launch.py   # Ctrl+C 停止
```

MP4 保存到包内 resource 目录，640×400, 15fps, mp4v。

## 网络

| 设备 | IP | 接口 |
|------|-----|------|
| RDK X5 | 192.168.127.10 | eth0（有线） |
| RDK X5 | 10.119.149.117 | wlan0（WiFi） |
| 另一台 | 192.168.127.1/24 | eno1（有线） |

## 性能

| 指标 | 值 |
|------|-----|
| BPU 推理 | ~22ms |
| Python 解码 | ~15ms |
| 端到端 | ~37ms (~27fps) |
| 模型输入 | 640×640 NV12 |
| 预处理 | letterbox 保比例 |

## 技术要点

- **libpostprocess.so 废弃**：该库硬编码 80 类 COCO，自定义模型会段错误。改用纯 Python 解码。
- **letterbox**：640×400 → 上下补灰边 → 640×640，保持物体比例。
- **两阶段 sigmoid**：先 bbox+obj 预过滤，幸存者做完整类别计算，减少 90% 计算量。
- **宽高不乘 stride**：anchor 定义在输入图空间，只中心坐标乘 stride。
