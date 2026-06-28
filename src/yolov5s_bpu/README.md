# yolov5s_bpu

Horizon RDK X5 BPU YOLOv5 检测 + Aurora930 深度相机 + Web 可视化，一键启动。

## 硬件

- 地平线 RDK X5
- Deptrums Aurora 930（USB 深度相机）

## 包结构

```
yolov5s_bpu/
├── launch/
│   ├── yolov5s_bpu.launch.py     # 一键启动(相机+BPU+Web)
│   └── record.launch.py          # 录制 MP4
├── yolov5s_bpu/
│   ├── yolov5s_bpu_node.py       # BPU 推理节点
│   └── record_node.py            # 录制节点
├── package.xml / setup.py / setup.cfg
```

## 数据流

```
Aurora 930 (640×400 BGR8, ~15fps)
        │
        ▼
yolov5s_bpu_node
  ├─ BGR → letterbox 保比例 → 上下补灰边 → 640×640
  ├─ BGR → YUV420 → NV12
  ├─ BPU forward (hobot_dnn)
  ├─ 纯 Python YOLOv5 解码 + cv2.dnn.NMSBoxes
  ├─ bbox 中心 7×7 邻域深度中值
  ├─ → /image_jpeg           (CompressedImage, ~15Hz)
  ├─ → /hobot_dnn_detection   (PerceptionTargets, ~15Hz)
  └─ → /detections            (DetectionArray, ~15Hz)
        │
        ▼
websocket :8080 + nginx :8000 → 浏览器
```

## 模型配置

配置目录：`/root/dev_ws/src/config/`

| 配置 | 类数 | 标签 | 模型输入 |
|------|------|------|----------|
| `weaponconfig` | 3 | lance, fist, hand | 640×640 |
| `redconfig` | 31 | R_R1, RT_01-15, RF_01-15 | 640×640 |
| `blueconfig` | 31 | B_R1, BT_01-15, BF_01-15 | 640×640 |

每个目录包含：
- `yolov5sconfig.json` — 模型参数
- `converted_model.bin` — BPU 量化模型 (7.5MB)
- `custom.list` / `obstacles.list` — 类别名

### yolov5sconfig.json 参数

| 参数 | weaponconfig | red/blue | 说明 |
|------|-------------|----------|------|
| `model_file` | 绝对路径 | 绝对路径 | .bin 位置 |
| `class_num` | 3 | 31 | 类别数 |
| `score_threshold` | 0.2 | 0.2 | 置信度阈值 |
| `nms_threshold` | 0.65 | 0.5 | NMS IoU |
| `nms_top_k` | 5000 | 500 | NMS Top-K |
| `strides` | [8,16,32] | [8,16,32] | 检测头 |
| `anchors_table` | COCO anchors | — | 锚框(可选) |

## 编译

```bash
cd ~/dev_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select detection_interfaces yolov5s_bpu
source ~/dev_ws/install/setup.bash
```

## 运行

```bash
# 武器检测（默认）
ros2 launch yolov5s_bpu yolov5s_bpu.launch.py

# 切换模型
ros2 launch yolov5s_bpu yolov5s_bpu.launch.py \
  config_file:=/root/dev_ws/src/config/redconfig/yolov5sconfig.json

# 录制 MP4（仅相机+Web，不跑 BPU）
ros2 launch yolov5s_bpu record.launch.py    # Ctrl+C 停止保存
```

浏览器 `http://<IP>:8000`

## 话题

| 话题 | 类型 | 频率 | 说明 |
|------|------|------|------|
| 订阅 `/aurora/rgb/image_raw` | Image(BGR8) | ~15Hz | 相机 640×400 |
| 订阅 `/aurora/depth/image_raw` | Image(16UC1) | ~15Hz | 深度 mm |
| 发布 `/image_jpeg` | CompressedImage | ~15Hz | Web 显示 (JPEG ~30KB) |
| 发布 `/hobot_dnn_detection` | PerceptionTargets | ~15Hz | 检测结果 (Web) |
| 发布 `/detections` | DetectionArray | ~15Hz | 检测结果 (归一化+深度) |

## 检测标签格式

`类名 置信度 深度mm`，如 `fist 0.84 737mm`

## 性能 (weapon 模型, 640×640)

| 阶段 | 耗时 |
|------|------|
| BPU 推理 | ~22ms |
| 解码+NMS | ~15ms |
| 总计 | ~37ms (~27fps) |

## 预处理

letterbox 保持宽高比：640×400 → 等比缩放 → 上下补灰边 → 640×640。后处理去除 padding 偏移后还原。

## 后处理

纯 Python YOLOv5 解码，不依赖 `libpostprocess.so`（该库硬编码 80 类导致自定义模型段错误）。两阶段 sigmoid 减少计算量，anchors/strides/class_num 从 JSON 配置读取。

## 深度标注

bbox 中心 7×7 邻域取深度中值，过滤零点。

## 依赖

- `rclpy`, `sensor_msgs`, `ai_msgs`, `std_msgs`
- `hobot_dnn` / `hobot_dnn_rdkx5`
- `numpy`, `cv2` (opencv-python)
- `detection_interfaces` (自定义消息)
- `deptrum-ros-driver-aurora930`
- `websocket` (地平线 Web 包)
