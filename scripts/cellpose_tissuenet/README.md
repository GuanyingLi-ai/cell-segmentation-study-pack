# Cellpose / TissueNet HIL 真值训练对照

本目录包含三组实验所用脚本：

- `reproduce_baseline.py`：载入指定模型，在固定 test split 推理并计算实例指标、保存 mask 与 QC 图。
- `train_finetune.py`：从 legacy `cyto` 权重开始，在 5 张人工标注图上微调 100 epochs。
- `train_from_scratch.py`：不载入预训练权重，以相同数据和训练参数随机初始化训练 100 epochs。

完整数据版本、环境、参数、指标与实验边界见 [`../../records/Cellpose_TissueNet_真值训练复现.md`](../../records/Cellpose_TissueNet_真值训练复现.md)。

注意：脚本保留了本次工作区的默认绝对路径，以确保本次运行可追溯。若在其他机器复跑，请先修改脚本顶部的数据根目录和输出根目录；不要将 test split 改作训练输入。
