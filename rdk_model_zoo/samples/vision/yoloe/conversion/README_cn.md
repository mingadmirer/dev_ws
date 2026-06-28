简体中文 | [English](./README.md)

# YOLOE 转换说明

本目录说明 YOLOE-11 Seg Prompt-Free 在 RDK X5 上的转换流程。

---

## 转换资源

当前保留的参考转换文件如下：

- `onnx_export/export_yoloe11seg_bpu.py` — 适配 BPU 的 ONNX 导出脚本
- `ptq_yamls/yoloe11s_seg_pf_bayese_640x640_nv12.yaml` — PTQ 量化配置

---

## 输出协议

YOLOE-11 Seg Prompt-Free 模型在 X5 上使用以下输出协议：

- 输入：`1x3x640x640`，`UINT8`，`NV12`
- 输出 0：分类头（stride 8）
- 输出 1：边界框头（stride 8，DFL 16 bins）
- 输出 2：掩码系数头（stride 8）
- 输出 3：分类头（stride 16）
- 输出 4：边界框头（stride 16，DFL 16 bins）
- 输出 5：掩码系数头（stride 16）
- 输出 6：分类头（stride 32）
- 输出 7：边界框头（stride 32，DFL 16 bins）
- 输出 8：掩码系数头（stride 32）
- 输出 9：原型张量

本 sample 的 Python runtime 使用这一协议，并采用 DFL 框解码与原型掩码生成逻辑。

---

## 转换步骤

### 1. 环境准备

克隆官方 YOLOE 仓库并安装依赖：

```bash
git clone https://github.com/um-assn/yoloe.git
cd yoloe
pip install -r requirements.txt
pip install ultralytics
```

下载匹配的预训练权重：

```bash
wget https://github.com/um-assn/yoloe/releases/download/v0.1/yoloe-11s-seg-pf.pt
```

### 2. 导出 ONNX

导出脚本（`export_yoloe11seg_bpu.py`）对模型进行了两项关键适配：

- 将 Linear 词汇层替换为等价的 1x1 Conv2d 层
- 修改检测头 forward 方法，输出 10 个 NHWC 布局的张量

同时将 4585 类词汇保存为 `.names` 文件。

执行导出：

```bash
python3 export_yoloe11seg_bpu.py --weights yoloe-11s-seg-pf.pt --imgsz 640
```

此步骤生成 `yoloe-11s-seg-pf.onnx` 和 `yoloe_seg_pf_classes.names`。

### 3. 准备校准数据

准备 640x640 分辨率的 RGB float32 校准图像数据集：

```bash
# 将校准图像放置在 ./calibration_data_rgb_f32_640/ 目录下
```

### 4. PTQ 量化转换

运行 `hb_mapper` 将 ONNX 模型转换为 BPU BIN 模型：

```bash
hb_mapper makertbin --model-type onnx --config yoloe11s_seg_pf_bayese_640x640_nv12.yaml
```

### 5. 验证

可视化编译后的模型：

```bash
hb_perf yoloe-11s-seg-pf_bayese_640x640_nv12.bin
```

查看模型输入输出：

```bash
hrt_model_exec model_info --model_file yoloe-11s-seg-pf_bayese_640x640_nv12.bin
```

---

## 说明

- 本文档聚焦 YOLOE 在 RDK X5 上的转换步骤。
- 运行时直接使用转换后的 `.bin` 模型，并通过 `hbm_runtime` 在 RDK X5 上执行。
- 注意力层中的 Softmax 节点配置为在 BPU 上以 int16 输入/输出运行以获得最佳性能。
- benchmark 图片和其他参考资料可在 `test_data/` 与相关仓库资源中查看。
