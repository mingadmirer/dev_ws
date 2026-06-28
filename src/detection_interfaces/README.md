# detection_interfaces

自定义 ROS2 检测消息接口包。

## 消息定义

### DetectionResult

单帧单物体检测结果。

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 物品名称 |
| `x1` | float32 | 左上角 x（归一化 0~1） |
| `y1` | float32 | 左上角 y（归一化 0~1） |
| `x2` | float32 | 右下角 x（归一化 0~1） |
| `y2` | float32 | 右下角 y（归一化 0~1） |
| `confidence` | float32 | 置信度 |
| `depth_mm` | float32 | 深度值 (mm) |
| `timestamp` | builtin_interfaces/Time | 检测时间戳 |

### DetectionArray

一帧内所有检测结果。

| 字段 | 类型 | 说明 |
|------|------|------|
| `header` | std_msgs/Header | 帧头（时间戳 + frame_id） |
| `detections` | DetectionResult[] | 检测结果数组 |

## 依赖

- `builtin_interfaces`
- `std_msgs`
- `rosidl_default_generators`

## 编译

```bash
cd ~/dev_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select detection_interfaces
```

## 话题

| 话题 | 类型 | 频率 | 说明 |
|------|------|------|------|
| `/detections` | DetectionArray | ~15Hz | 检测结果 |

## 示例

```bash
ros2 topic echo /detections --once
```

输出：
```yaml
header:
  stamp: {sec: 1782648699, nanosec: 984317900}
  frame_id: rgb_camera_link
detections:
- name: fist
  x1: 0.492
  y1: 0.583
  x2: 0.647
  y2: 0.685
  confidence: 0.841
  depth_mm: 737.0
- name: hand
  x1: 0.822
  y1: 0.295
  x2: 0.881
  y2: 0.671
  confidence: 0.556
  depth_mm: 829.0
```
