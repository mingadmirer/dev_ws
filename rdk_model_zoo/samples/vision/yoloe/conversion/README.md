English | [简体中文](./README_cn.md)

# YOLOE Conversion

This directory describes the conversion workflow of YOLOE-11 Seg Prompt-Free for RDK X5.

---

## Conversion Assets

The following files are kept as the reference conversion resources:

- `onnx_export/export_yoloe11seg_bpu.py` — ONNX export script with BPU-compatible patches
- `ptq_yamls/yoloe11s_seg_pf_bayese_640x640_nv12.yaml` — PTQ quantization configuration

---

## Output Protocol

The YOLOE-11 Seg Prompt-Free model on X5 uses the following output protocol:

- Input: `1x3x640x640`, `UINT8`, `NV12`
- Output 0: classification head (stride 8)
- Output 1: bounding-box head (stride 8, DFL 16 bins)
- Output 2: mask-coefficient head (stride 8)
- Output 3: classification head (stride 16)
- Output 4: bounding-box head (stride 16, DFL 16 bins)
- Output 5: mask-coefficient head (stride 16)
- Output 6: classification head (stride 32)
- Output 7: bounding-box head (stride 32, DFL 16 bins)
- Output 8: mask-coefficient head (stride 32)
- Output 9: prototype tensor

The Python runtime in this sample uses this contract and decodes it with DFL box regression and prototype mask generation.

---

## Conversion Steps

### 1. Environment Preparation

Clone the official YOLOE repository and install dependencies:

```bash
git clone https://github.com/um-assn/yoloe.git
cd yoloe
pip install -r requirements.txt
pip install ultralytics
```

Download the matching pretrained weights:

```bash
wget https://github.com/um-assn/yoloe/releases/download/v0.1/yoloe-11s-seg-pf.pt
```

### 2. Export to ONNX

The export script (`export_yoloe11seg_bpu.py`) applies two critical patches for BPU compatibility:

- Replaces Linear vocabulary layers with equivalent 1x1 Conv2d layers
- Patches the detection head forward method to output 10 tensors in NHWC layout

It also saves the 4585-class vocabulary to a `.names` file.

Run the export:

```bash
python3 export_yoloe11seg_bpu.py --weights yoloe-11s-seg-pf.pt --imgsz 640
```

This produces `yoloe-11s-seg-pf.onnx` and `yoloe_seg_pf_classes.names`.

### 3. Prepare Calibration Data

Prepare a calibration dataset of RGB float32 images at 640x640 resolution:

```bash
# Place calibration images in ./calibration_data_rgb_f32_640/
```

### 4. PTQ Conversion

Run `hb_mapper` to convert the ONNX model to a BPU BIN model:

```bash
hb_mapper makertbin --model-type onnx --config yoloe11s_seg_pf_bayese_640x640_nv12.yaml
```

### 5. Validation

Visualize the compiled model:

```bash
hb_perf yoloe-11s-seg-pf_bayese_640x640_nv12.bin
```

Check model inputs and outputs:

```bash
hrt_model_exec model_info --model_file yoloe-11s-seg-pf_bayese_640x640_nv12.bin
```

---

## Notes

- This document focuses on the conversion steps required for YOLOE on RDK X5.
- The runtime uses converted `.bin` models through `hbm_runtime`.
- The Softmax node in the attention layer is configured to run on BPU with int16 input/output for optimal performance.
- Benchmark figures and additional reference assets are available under `test_data/` and related repository resources.
