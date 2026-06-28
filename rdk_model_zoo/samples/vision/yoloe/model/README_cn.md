简体中文 | [English](./README.md)

# YOLOE 模型文件

该目录保存 `yoloe` sample 使用的 `*.bin` 模型下载说明。

- 目标平台：`RDK X5`
- 模型格式：`.bin`
- 默认运行模型：`yoloe-11s-seg-pf_bayese_640x640_nv12.bin`

## 下载

运行下载脚本获取模型：

```bash
bash download_model.sh
```

脚本会将模型文件下载到当前目录。

## 可用模型

### Bayes-e (RDK X5 & RDK X5 Module)

#### bin - nv12

YOLOE-11s-Seg-PF

```bash
wget https://archive.d-robotics.cc/downloads/rdk_model_zoo/rdk_x5/AAA_RDK_YOLO/yoloe-11s-seg-pf_bayese_640x640_nv12.bin
```
