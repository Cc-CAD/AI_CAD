# AI_CAD

CAD 练习与迭代成果，包含二维工程图、三维零件和水刀切割定位夹具。这里共享的是 CAD 文件和经练习形成的制图要求，不是模型训练权重。

## 模型与图纸

| 案例 | 二维图纸 | 三维模型 |
|---|---|---|
| 阶梯轴 | [DXF](models/cad_practice_2/01_stepped_shaft/stepped_shaft_D.dxf) | [STEP](models/cad_practice_2/01_stepped_shaft/stepped_shaft.step) |
| 加强筋沉孔支座 | [DXF](models/cad_practice_2/02_counterbore_bracket/counterbore_bracket_D.dxf) | [STEP](models/cad_practice_2/02_counterbore_bracket/counterbore_bracket.step) |
| 对称支架 | [DXF](models/complex_part/symmetric_bracket_2_1M.dxf) | [STEP](models/complex_part/symmetric_bracket.step) |
| NAAMS ASP230 板件 | [DXF](models/part_drawing/NAAMS_ASP230_corrected.dxf) | [STEP](models/part_drawing/NAAMS_ASP230.step) |
| 长方体三视图 | [DXF](models/step_three_views/cuboid_three_views.dxf) | [STEP](models/step_three_views/cuboid_source.step) |

水刀定位、夹紧与支撑夹具：

- [对称支架夹具 STEP](models/complex_part/水切模具/symmetric_bracket_waterjet_fixture_multibody.step)
- [ASP230 夹具 STEP](models/part_drawing/水切模具/NAAMS_ASP230_waterjet_fixture_multibody.step)

## 使用

下载 DXF 后用 AutoCAD 或兼容软件打开，STEP 可用于支持该格式的三维 CAD 软件。成品几何采用毫米和 1:1 尺寸；辅助视图的绘图比例见图纸标记。STEP 采用单零件文件，夹具包含多个实体。

[AGENTS.md](AGENTS.md) 记录单位、原生圆弧、尺寸比例、箭头、线宽、标注避让、标题栏和交付规则。模型目录仅保留当前有效的 DXF 和 STEP。

这些文件用于练习；部分缺失尺寸、材料和公差由练习设计补充，图纸校核状态见标题栏。文件检查与渲染预览不等于在 AutoCAD 中实测，也不等于完成生产审批。

## 练习来源

- 阶梯轴：Pragmatic Metrology 的 PM-01 A1，[原题页面](https://www.pragmaticmetrology.com/p/drawings-and-exercises.html)。
- 加强筋支座：[Autodesk 官方建模练习](https://files.upskill-dev.autodesk.com/public/aex/fusion/Sketching_Part_Modeling_2026/260201_M1-CE_Direct-modeling.pdf)。
- 其他案例来自此前的公开零件图练习或用户提供的 STEP。

原题资料的权利归各自作者所有。评分包 inputs 附原评测所用题目 PDF，原资料的权利仍归原作者；私有仓库用于练习复现，不代表获得源资料再许可。

## 程序化评分

[benchmark 评分代码及运行说明](benchmark/README.md) 包含原始 CAD 回归评分和 BenchCAD 风格体素 IoU 评分、冻结参考及自检。
