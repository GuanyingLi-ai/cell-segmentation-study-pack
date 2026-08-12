# CellSAM 论文结果级最小复现

本实验使用 CellSAM 官方仓库随附的 YeaZ 图像和作者发布的实例预测，重新生成实例统计、逐细胞测量、mask 面板和边界叠加图。

## 执行

从学习包根目录运行：

```bash
python scripts/cellsam/reproduce_yeaz.py
```

成功标准：命令退出码为 0，输出中 `cell_count` 为 95，且四个产物均可读取。

## 复现边界

这是“官方结果的独立读取、统计和可视化复现”，不是本机重新执行 CellSAM v1.2 权重推理。官方权重受非商业学术许可约束，必须通过 DeepCell 用户令牌下载；完整评估集约 14 GB，解压约 84 GB。

获得令牌后可执行模型推理：

```bash
export DEEPCELL_ACCESS_TOKEN='...'
python -m pip install 'cellSAM @ git+https://github.com/vanvalenlab/cellSAM.git'
python scripts/cellsam/reproduce_yeaz.py \
  --run-model \
  --mask outputs/cellsam/yeaz/fresh_prediction.npy
```

令牌不得写入脚本、记录或版本库。
