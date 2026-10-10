# BenchCAD 风格评分 v2

主分为两个零件 STEP 对冻结参考的平均归一化体素 IoU（0–1，64³ 网格），失败计零。上游 iou.py 保持原样，出处提交见 upstream/commit.txt，许可证见 upstream/LICENSE。夹具复现分数、绝对坐标体积 IoU 和工程检查分别报告，不计入主分。本任务使用 PDF/OCP，不是 BenchCAD 官方四视图任务，不可与官方排行榜比较。

在仓库根目录运行（建议 Python 3.12 虚拟环境）：

```shell
python -m pip install -r benchmark/cad_case_v2_benchcad/requirements.txt
python benchmark/cad_case_v2_benchcad/selftest.py
python benchmark/cad_case_v2_benchcad/engineering.py --candidate-root models --report benchmark/results/engineering.json
python benchmark/cad_case_v2_benchcad/evaluate.py --candidate-root submission/output --report benchmark/results/run001/evaluation.json
```

完整评分要求 submission/generate.py、同目录 Python 模块、submission/TASK.md（从本版复制）和 submission/inputs。评分器把代码和 inputs 复制到空的 replay_work，限时 30 秒执行 generate.py，在该目录重建 output 下的六个成果；不能只提交预生成 STEP。每次报告使用新目录，避免覆盖 replay_work。任务及六个文件路径见 TASK.md。

工程检查可直接评候选 DXF/STEP，不要求生成代码。reference 和 spec.json 是冻结回归基准，不随 models 内后来修改的图纸改变。归一化 IoU 会掩盖统一缩放/移动，必须同时查看毫米尺寸和绝对体积指标。箭头、排版、真实 CAD 导入和夹具强度不在自动验证范围内。

仅在隔离环境运行可信的提交代码；replay_work 和超时不构成操作系统沙箱。inputs 包含原题 PDF 和固定夹具设计，后者使夹具任务成为复现任务，不是自由设计评价。

protocol_manifest.json 保留历史运行的冻结记录；本次发布的文件校验记录在 ../release_manifest.json，历史报告不可用新文件哈希替代。发布仅调整默认候选路径、运行说明和 v1 自检路径，评分算法、spec、原参考、上游评分器未改变。未打包历史 API 调用驱动、日志或缓存，本包评分无需 API 密钥。
