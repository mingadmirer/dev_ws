#!/usr/bin/env python3

# Copyright (c) 2026 D-Robotics Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Export YOLOE-11 Seg Prompt-Free model to ONNX for BPU deployment.

This script modifies the YOLOE model's vocabulary layers from Linear to
Conv2d (BPU-compatible) and patches the forward method to output 10 tensors
in NHWC layout. It also saves the 4585-class vocabulary to a .names file.

Usage:
    python3 export_yoloe11seg_bpu.py --weights yoloe-11s-seg-pf.pt --imgsz 640
"""

import argparse
from types import MethodType

import torch.nn as nn
from ultralytics import YOLO


def linear2conv(linear: nn.Linear) -> nn.Conv2d:
    """Replace a Linear layer with an equivalent 1x1 Conv2d for BPU."""
    assert isinstance(linear, nn.Linear), "Input must be a Linear layer."
    conv = nn.Conv2d(
        in_channels=linear.in_features,
        out_channels=linear.out_features,
        kernel_size=1,
        stride=1,
        padding=0,
        bias=linear.bias is not None,
    )
    conv.weight.data = linear.weight.view(linear.out_features, linear.in_features, 1, 1).data
    if linear.bias is not None:
        conv.bias.data = linear.bias.data
    return conv


def rdk_forward(self, x, text):
    """Forward method patched for BPU output layout (NHWC, 10 tensors)."""
    results = []
    for i in range(self.nl):
        results.append(self.lrpc[i].vocab(self.cv3[i](x[i])).permute(0, 2, 3, 1).contiguous())
        results.append(self.lrpc[i].loc(self.cv2[i](x[i])).permute(0, 2, 3, 1).contiguous())
        results.append(self.cv5[i](x[i]).permute(0, 2, 3, 1).contiguous())
    results.append(self.proto(x[0]).permute(0, 2, 3, 1).contiguous())
    return results


def main():
    parser = argparse.ArgumentParser(description="Export YOLOE-11 Seg PF to ONNX for BPU")
    parser.add_argument("--weights", type=str, default="yoloe-11s-seg-pf.pt",
                        help="Path to YOLOE pre-trained weights.")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Input image size for export.")
    parser.add_argument("--opset", type=int, default=11,
                        help="ONNX opset version.")
    parser.add_argument("--names-output", type=str, default="yoloe_seg_pf_classes.names",
                        help="Output path for the class names file.")
    args = parser.parse_args()

    model = YOLO(args.weights)

    # Replace Linear vocab layers with Conv2d for BPU compatibility
    model.model.model[23].lrpc[0].vocab = linear2conv(model.model.model[23].lrpc[0].vocab)
    model.model.model[23].lrpc[1].vocab = linear2conv(model.model.model[23].lrpc[1].vocab)
    model.model.model[23].forward = MethodType(rdk_forward, model.model.model[23])

    # Save class names (4585 entries)
    with open(args.names_output, "w", encoding="utf-8") as f:
        for name in model.names.values():
            f.write(f"{name}\n")
    print(f"Saved {len(model.names)} class names to {args.names_output}")

    # Export to ONNX
    model.export(imgsz=args.imgsz, format="onnx", simplify=True, opset=args.opset)
    print("Export complete.")


if __name__ == "__main__":
    main()
