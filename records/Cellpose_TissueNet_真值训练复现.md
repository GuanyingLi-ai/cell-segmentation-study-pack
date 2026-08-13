# 复现记录：Cellpose / TissueNet HIL 真值训练对照

## 1. 目标与状态

- 目标：在带人工实例真值的数据上，对比 legacy `cyto` 预训练直接推理、预训练后微调、随机初始化从零训练。
- 状态：**成功**（2026-08-13）。
- 范围：小样本训练对照；不是 Cellpose 2021 论文全数据训练或完整 benchmark 复算。
- 操作者：liguanying / Codex 辅助执行。
- 对应论文：Stringer C, et al. *Cellpose: a generalist algorithm for cellular segmentation*. Nature Methods 18, 100–106 (2021)；数据来自 Cellpose 2.0 human-in-the-loop 示例。

## 2. 可追溯信息

- 软件：`cellpose==3.1.1.1`。
- 基础 checkpoint：legacy `cyto` / `cytotorch_0`。
- 基础模型 SHA-256：`6a852487b98a3ad91e4e86c969cac520aaac13c609288aad8bd01d4cf76370c6`。
- 数据：Figshare 归档 `20510016`，Cellpose 2.0 human-in-the-loop TissueNet 小数据集。
- 原始 ZIP SHA-256：`f94ea40a7f54fbb1af2e1ffcbed87cd4be7db53db1d3b7d79f4ec6eeef5696ee`。
- 执行脚本：`scripts/cellpose_tissuenet/reproduce_baseline.py`、`train_finetune.py`、`train_from_scratch.py`。
- 完整指标：`outputs/cellpose_tissuenet/*/metrics.json` 和 `training_metrics.json`。
- 随机种子：0。

## 3. 计算环境

| 项目 | 记录 |
|---|---|
| OS | macOS 26.0 arm64 |
| CPU / GPU | Apple Silicon；固定 CPU 训练与推理 |
| Python | 3.12.13 |
| Cellpose | 3.1.1.1 |
| PyTorch | 2.13.0 |
| NumPy | 2.0.2 |
| 容器 | 未使用 |

## 4. 数据

- 平台/组织：TissueNet 双通道细胞图像；包含 `breast_vectra` 等样本。
- 训练集：5 张 `2×256×256` 图像，644 个人工实例。
- 验证集：未单独划分；因此没有用验证集选 epoch 或阈值。
- 测试集：固定 3 张 `2×256×256` 图像，564 个人工实例。
- gold standard：Cellpose `_seg.npy` 中的人工实例 `masks`，0 为背景，1…N 为实例标签。
- 隔离方式：三个实验仅使用 5 张 train 图训练；3 张 test 图只用于最终评价，未参与训练。
- 分子表、配准：不适用，本实验是纯图像实例分割。

## 5. 预处理

| 步骤 | 参数 | 输入 | 输出 | 备注 |
|---|---|---|---|---|
| 读取图像与标签 | `mask_filter=_seg.npy` | 双通道图、人工 mask | 训练/测试数组 | 保留官方划分 |
| 通道映射 | `[2,1]` | 两个图像通道 | Cellpose 输入 | 三组一致 |
| 尺度归一 | Cellpose 默认；`diameter=30` | 原始强度 | 网络输入 | 三组推理一致 |
| 实例评价 | 一对一匹配 | 预测/真值实例 | TP、FP、FN、F1、PQ | 阈值 0.50、0.75、0.90 |

## 6. 模型/推断参数

| 参数 | 值 | 适用实验 | 选择依据 |
|---|---:|---|---|
| diameter | 30 | 三组推理 | legacy cyto 常用配置 |
| flow threshold | 0.4 | 三组推理 | Cellpose 默认 |
| cellprob threshold | 0.0 | 三组推理 | Cellpose 默认 |
| min size | 15 | 三组推理 | 排除极小伪实例 |
| epochs | 100 | 微调、从零训练 | 严格对照固定值 |
| learning rate | 0.005 | 微调、从零训练 | 两组一致 |
| weight decay | 1e-5 | 微调、从零训练 | 两组一致 |
| batch size | 5 | 微调、从零训练 | 覆盖全部训练图 |
| optimizer | Adam | 微调、从零训练 | `SGD=False` |
| scratch 初始化 | `pretrained_model=False`, `model_type=None` | 从零训练 | 明确不载入官方权重 |

## 7. 运行记录

- 预训练直接推理：载入 `cytotorch_0`，在固定测试集推理并评价。
- 微调：载入同一预训练权重，在 5 张训练图上训练 100 epochs，再评价固定测试集。
- 从零训练：相同网络结构、数据、种子和超参数，随机初始化后训练 100 epochs。
- 从零训练 wall time：330.77 s；微调 wall time：388.63 s。
- warning：PyTorch sparse invariant warning；未导致进程失败、空 mask 或无效输出。
- 完整命令逻辑与参数见三个脚本；训练 checkpoint 均已保存到输出目录。

## 8. 结果

### 图像实例指标

| 实验 | IoU 阈值 | TP | FP | FN | Precision | Recall | F1 | 匹配均值 IoU | PQ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 预训练直接推理 | 0.50 | 179 | 37 | 385 | 0.829 | 0.317 | 0.459 | 0.696 | 0.319 |
| 预训练后微调 | 0.50 | 233 | 59 | 331 | 0.798 | 0.413 | **0.544** | 0.683 | **0.372** |
| 随机初始化从零训练 | 0.50 | 141 | 57 | 423 | 0.712 | 0.250 | 0.370 | 0.682 | 0.253 |
| 预训练直接推理 | 0.75 | 57 | 159 | 507 | 0.264 | 0.101 | 0.146 | 0.797 | 0.116 |
| 预训练后微调 | 0.75 | 63 | 229 | 501 | 0.216 | 0.112 | **0.147** | 0.794 | **0.117** |
| 随机初始化从零训练 | 0.75 | 36 | 162 | 528 | 0.182 | 0.064 | 0.094 | 0.789 | 0.075 |

说明：这里的 `F1` 是实例匹配 F1，不是像素 Dice；`PQ = F1 × 匹配实例平均 IoU`。未计算 Dice、AJI、分子与生物指标，不用其他量冒充。

### 产物

- 预训练结果：`outputs/cellpose_tissuenet/baseline_legacy_cyto/`。
- 微调 checkpoint：`outputs/cellpose_tissuenet/finetune_legacy_cyto/models/`。
- 微调测试结果：`outputs/cellpose_tissuenet/finetuned_eval/`。
- 从零训练 checkpoint：`outputs/cellpose_tissuenet/scratch_legacy_architecture/models/`。
- 从零训练测试结果：`outputs/cellpose_tissuenet/scratch_eval/`。
- 各评价目录包含逐图 mask、QC 图和 `metrics.json`。

## 9. 偏差分析

- 一致部分：三组使用完全相同的测试集、通道、后处理阈值和实例匹配评价，训练对照只改变初始化来源。
- 微调在 IoU≥0.50 时将 TP 从 179 提高到 233，Recall 从 0.317 提高到 0.413；同时 FP 从 37 增至 59，Precision 略降。
- 微调在 IoU≥0.75 时提升很小，说明小样本训练主要减少漏检，未明显改善严格边界质量。
- 从零训练在两个阈值下均较差，说明 5 张图不足以替代预训练阶段积累的通用表征。
- 局限：训练仅 5 张、测试仅 3 张；只有随机种子 0；没有 validation split；100 epochs 和阈值未经独立调优。
- 典型风险：密集区域合并、弱信号漏检、边界不精确；逐图 QC 应与汇总指标一起检查。

## 10. 结论与下一步

- 是否达到复现标准：达到“小样本真值训练对照可运行、可追溯、可定量评价”的标准。
- 推荐方案：当前数据规模下采用官方预训练权重后微调，不推荐随机初始化从零训练作为最终模型。
- 是否可用于全切片：尚不能；必须先扩大数据与 ROI，并验证内存、速度和 patch 边界。
- 下一实验只改变一个变量：保持其余配置不变，增加训练样本量，并划出 validation set 选择 epoch。
- 决策：预训练微调继续验证；随机初始化组保留为消融基线。
