# 模式、项目身份与设计阶段

## 三种模式

| 模式 | 实际工作 | 可交付结论 |
|---|---|---|
| quick 快速初筛 | 全册身份/目录清点，优先安全、保护红旗、明显图文矛盾；允许仅重点页放大 | 部分检查报告，保留未审页/项；不得称全面合规 |
| detailed 详细审查 | 所有可读页面视觉检查，全部路由原子项、跨图复查、适用性和反证 | 已审范围内的逐项意见；资料不足独列 |
| specialty 专项复核 | 指定模块 + identity/consistency；核查相关跨专业与保护约束 | 专项范围结论；其余专业明确未覆盖 |

V1 quick 与 detailed 使用相同检查母表，区别在执行深度和完成范围；脚本不自动审图。specialty 支持 identity、consistency、planning、fire、accessibility、sanitary、structure、heritage、district、appearance、systems、construction。

## 身份路由

`heritage_work=true`：文物、历史建筑、传统风貌建筑的修缮或保护范围影响。身份未知时用 null，保护模块列 candidate 继续查证，不能跳过。明确普通建筑且不涉保护范围才可 false 并在身份表记录证据。

`district_update=true`：多地块/街巷/公共空间/分期更新；未知用 null。其他共性模块始终列入检查；路由仅为发现线索，不证明某规范适用。

保护身份采用：cultural_relic_protected、immovable_relic、historic_building、traditional_character、ordinary_in_protected_area、ordinary、unknown。记录名录名称、对象编号、官方链接、核验日期、保护规划范围与要素；“未搜到”不能证明 ordinary。不同建筑可有不同身份，在 intervention_scope 中逐栋标识，单一 profile 值用 mixed 并逐项匹配。

## 阶段路由（审查人执行并记录）

| stage | 优先判断 | 不足时处理 |
|---|---|---|
| concept 概念/汇报 | 功能、规模、场地、保护策略、重大实施障碍 | 详细尺寸缺失列下阶段核实，不据此判违规 |
| planning 报规方案 | 总图、指标、风貌、改造边界、主要功能与安全组织 | 深度问题需先核实本阶段应提供内容 |
| preliminary 初设 | 方案协调、构造策略、结构与机电接口、性能与专项论证 | 详细技术结论需可读细节及正式条文 |
| construction 施工图 | 细节、尺寸、材料工艺与跨图一致性 | 本技能仍属辅助复核，不能替代法定审图 |
| unknown/null | 已可观察事实、矛盾和补充资料 | 阻断阶段依赖的确定合规判断 |

初始化时根据已知阶段给每模块写入 `stage_focus`，对不明阶段保留核实任务。不得从文件名自动认定阶段。普通既有建筑不自动适用新建标准；本次改造范围外并非自动免除关联安全核实。用户已有审查意见时区分“复核其依据”与“发现新问题”，保留原文和修订轨迹。

## 原子检查状态

pending 未执行；insufficient 图纸/依据/适用性不足；not_applicable 有正向范围证据；conforming 在已核实正式依据下符合；violation 在明确强制性要求与足够证据下不符合；contradiction 项目内部图文矛盾；optimization 合理性建议。风险与确定性分开，高风险未知不得降为低价值建议。

目录或模块修改使检查清单失效，重新建新工作区并迁移真实事实，不覆盖旧报告。项目PDF变化同样需要新工作区；不要只改哈希续用已通过结论。

## 区位保护与报批前置核查

新项目初始化包含location_review台账，按[区位保护与报批核查](location-approvals.md)执行；十二模块数量不变。实际判断由模型查询官方资料完成，脚本不自动地理编码或叠加GIS。新增台账可用于旧项目继续补查，旧记录无该字段时报告标为未执行，不追认已查。身份或边界未解决时，依赖它的检查适用性保持unknown。
