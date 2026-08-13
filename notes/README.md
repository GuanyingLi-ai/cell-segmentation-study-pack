# 学习笔记

本目录存放 **概念理解、方法拆解、对话整理** 类笔记，与 `records/`（复现实验记录）和 `templates/`（空白模板）分工如下：

| 目录 | 用途 |
|------|------|
| `notes/` | 方法原理、流程梳理、术语解释、学习总结 |
| `records/` | 某次复现的环境、命令、指标、结论与限制 |
| `templates/` | 论文阅读、复现记录、方法比较的空白模板 |

## 笔记索引

| 笔记 | 主题 | 关联复现 |
|------|------|----------|
| [StarDist 方法学习笔记](StarDist_方法学习笔记.md) | 星凸参数化、prob/dist、中心检测、2D/3D 推理与复现边界 | [2D](../scripts/stardist/README.md) · [3D](../scripts/stardist/README_3D.md) |
| [Cellpose 方法学习笔记](Cellpose_方法学习笔记.md) | 概率图、XY 流场、pixel dynamics、训练/推理、参数与指标诊断 | [官方 demo](../records/Cellpose_预训练推理复现.md) · [TissueNet 真值训练](../records/Cellpose_TissueNet_真值训练复现.md) |
| [Baysor 方法学习笔记](Baysor_方法学习笔记.md) | 空间+基因联合聚类、MRF/BMM 流程、prior、参数与 smoke 复现边界 | [最小复现](../records/Baysor_Petukhov_复现.md) · [脚本](../scripts/baysor/README.md) |
| [SMURF 方法学习笔记](SMURF_方法学习笔记.md) | **原始 PDF**：[SMURF_原始笔记.pdf](SMURF_原始笔记.pdf) | 手写/扫描笔记 |
| [SOPA 方法学习笔记](SOPA_方法学习笔记.md) | **原始 PDF**：[SOPA_原始笔记.pdf](SOPA_原始笔记.pdf) | 手写/扫描笔记 |

## 推荐阅读顺序

1. 先读 [总框架](../00_总框架.md) 与 [方法总结](../01_方法总结.md)，明确方法所属类别  
2. 再读本目录对应方法笔记，建立原理、流程与术语框架  
3. 最后对照 `scripts/` 跑复现，用 `records/` 核对指标、实验边界和失败模式  

## 新增笔记约定

- 文件名：`方法名_主题.md`（如 `StarDist_方法学习笔记.md`）  
- 文首注明：整理来源、关联脚本/论文、最后更新日期  
- 在本 README 索引表中补一行链接  
