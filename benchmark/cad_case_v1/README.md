# CAD 回归评分 v1

此版本读取 DXF/STEP，检查几何、毫米单位、DIMLFAC、原生标注、分层、STEP 有效性、固定夹具实体数及多余 STEP。通过项按原评分权重计分；全部检查通过才算通过。

在仓库根目录运行（建议 Python 3.12 虚拟环境）：

```shell
python -m pip install -r benchmark/cad_case_v1/requirements.txt
python benchmark/cad_case_v1/evaluate.py --candidate-root models --report benchmark/results/v1.json
python benchmark/cad_case_v1/selftest.py
```

候选目录需包含 TASK.md 所列的六个相对路径。reference 是原评测冻结答案，spec.json 保存尺寸、容差和参考 SHA256；不随最新练习图纸改变。自检使用冻结参考，制造四类错误来验证检错能力。默认不传候选参数时仅评价冻结参考。长度比较容差 0.001 mm，不是制造公差。

v1 对轮廓表达方式和标注数量要求严格，语义等价的新画法可能失败；后续工程检查改进见 v2。高分不代表完成箭头、重叠、CAD 软件导入或夹具强度验证。此两案例回归评分不能代表一般 CAD 能力。

inputs 是原评测题目 PDF 和固定夹具设计输入，只向被测系统提供 inputs/TASK.md，不提供 reference/spec/评分代码。评测应在隔离环境进行。
