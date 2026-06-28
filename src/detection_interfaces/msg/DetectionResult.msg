# 单个检测结果
string   name              # 物品名称 (如 fist, lance, hand)
float32  x1                # 左上角 x (0~1, 归一化到图像宽度)
float32  y1                # 左上角 y (0~1, 归一化到图像高度)
float32  x2                # 右下角 x (0~1)
float32  y2                # 右下角 y (0~1)
float32  confidence        # 置信度
float32  depth_mm           # 深度值 (毫米)
builtin_interfaces/Time timestamp  # 检测时间戳
