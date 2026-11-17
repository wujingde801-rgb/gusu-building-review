# 证据、适用性与冲突处理

## 台账合同（review.json schema_version=1）

- inventory：物理页码page（1起）、printed_page、drawing_id、title、visual_status=unseen/seen/unreadable。图纸缺失不代表不存在设计措施。
- evidence：id、source_sha256、page、bbox=[left,top,right,bottom]，从按PDF旋转显示的页面左上角起，0..1归一化；path为真实截图绝对路径；sha256、observation、quality=clear/unclear。清晰度由实际看图判定；截图脚本默认 unclear。
- facts：id、observation、evidence_ids；数值事实另加 value、unit、object、dimension_basis=net/gross/unknown、来源标注。文字也需原页证据；只有OCR文字不足以证明位置关系。
- checks：稳定id、一个对象的一项question、result、fact_ids、comparison、action、risk；applicability八项关卡；counterevidence、basis、human。模板问题为发现入口，可在问题内指定实际对象，不能删掉未做的检查。
- verification_log：id、record_id、url、accessed_on、status_evidence（实施/废止/过渡公告位置和结果）、fulltext_locator（正式全文位置），可另记 issuer/issue_date/amendments/failure。网络不通应记录failure，不得补造访问成功。
- basis：source_type=online/local（旧记录未填默认local）；local使用record_id、revision、sha256；两类均须clause、excerpt（保留约束措辞与例外）、source_locator（正式原文页码/段落）、force=mandatory/recommended/informative、verification_id。

全图定位与局部清晰图可分别登记证据；门窗表、图例与平剖对应需各自证据。无须为了字段完整虚构图号，缺图号用“PDF第N页”。不能用缩略图像素按比例猜净宽；比例明确且无变形也只作复核线索，确定数值优先正式尺寸或设计方确认。

## 合规意见八项适用性关卡

identity 保护身份与用途；date 项目应适用日期及过渡条款；region 全国/江苏/苏州/姑苏范围；project_type 新建/改造/修缮/用途变更；stage 阶段深度；scope 改造范围与关联部位；exceptions 特别规定、豁免或获批专项方案；conflicts 来源冲突。每项 result=pass/unknown/fail，附 reason（必要时附证据ID）。任何 unknown/fail 阻断 conforming/violation。

B来源 effective 表示当前目录已核验，但仍需判断本项目适用时点。项目适用旧版时不能直接改成“旧版当前有效”；V1不自动处理历史时点法律适用，保留 insufficient，附旧版档案和过渡条款交人工复核。

90天为工具复核新鲜度策略，非法律有效期；即使不足90天，形成报告前也应查官方最新变更。不能仅凭日期和域名判定文件真实有效，必须读发文机关、正文、附件及修订信息。

## 冲突

记录每个来源名称、版本、发布机关、性质、实施范围、原文、条文与双方支持的事实，不以“地方更严”或“新版总优先”自动裁决。先区分同一问题还是适用范围不同，再查废止、替代、过渡、上位依据、专项批准权限。解释资料与案例不能推翻正式规范。疑似抵触、保护要求与消防/无障碍难以同时实现时，提出专项论证/主管部门或专业复核，保留双边证据，不自行批准豁免。

## 反证、措辞与数值

counterevidence.searched 为实际检查的 evidence IDs；result=consistent/none_found/conflict/unknown，记录具体reason。“未设置”至少查涉及楼层、图例和专项说明；未见与不存在分开。conflict/unknown不能关闭合规判断。

“不宜”应连同适用条件、例外和条文说明理解；不满足推荐指标可以列建议或待论证，不自动认定违法。厕所男女比例、无障碍卫生间形式、疏散净宽等没有预置阈值。每次回到真实正式原文，逐项核对统计口径、对象与例外。脚本未实现通用工程计算器，计算由审查人执行并记录输入、单位、算式、舍入与结果；脚本不验证算式的专业正确性。

## 规则库

assets/rule-template.json 是未启用示例。将规则JSON作为A层 kind=rule 资料通过知识库提案流程管理；元数据status=effective 且JSON status=active 才会展开 obligations。草稿不执行。每个义务一个ID/问题，required_facts、comparison_method、阈值与单位不允许从经验猜测。规则 basis 必须关联正式依据（本地B记录或在本项目重新核验的online依据），新增项目时快照 active 规则；所有本地规则以 candidate 列入，项目适用性须逐条判断。专项模式仍列本地规则，以便发现冲突；范围外的规则用正向事实标 not_applicable，不默默丢弃。规则库变更使旧校验失效，用新工作区重审受影响项并保留历史。

校验器检查引用完整性、哈希、状态、适用关卡、规则快照与明显矛盾；无法验证人是否真实看图、条文是否正确转述或确认人身份。人工复核记录只能来自用户实际回复，不能为通过校验填造。

## 引用链接输出

每次引用规范或标准，在对应意见旁使用 `[标准名称及编号](实际核对的详情URL)`，能取得公开全文时附 `[标准全文](全文URL)`。保留版本、条款号、PDF物理页/印刷页；网页不能直达条文时不要声称可直达条文。详情链接不等于全文可用。verification_log可补充title、fulltext_url；正式依据链接来自已核对的official_url或核验记录，不编造链接，不用搜索结果页。仅本地原文可用时提供绝对路径可点击文件链接，并注明未取得在线全文。Word/PDF输出须保留实际超链接。

## 线上依据与链接优先的保存方式

online与local是两条平行的正式依据路径，不将项目经验升级为法规。online不要求record_id/revision/sha256、不要求原文长期保存或正式入库；local保留既有B来源状态、版本和原文哈希校验。项目PDF及图纸证据的保存规则不变。

online的basis字段：source_type="online"、title（标准/文件名称）、standard_code（标准编号或正式文号）、version、issuer、url（已核对详情/官方正文）、effective_on、expires_on（可空）、status="effective"、clause、excerpt（简短约束措辞及例外）、source_locator（条号及页码/段落）、force、verification_id。历史适用旧版仍按本文件原规则保持insufficient交人工复核。

对应verification_log记录：唯一id、与basis完全一致的title/standard_code/version/url、accessed_on（实际核验日期）；source_authority=official或authorized_publication及authority_note（发布身份如何核实）；status_checked=true、status_url（实际核对的实施/修改/替代/废止公告）、status_evidence（核验结果）；fulltext_url、fulltext_status="read"、fulltext_locator；reviewed_clauses列表，每项为clause、source_locator、observation（实际读取该位置与上下文的观察）。引用的clause和source_locator必须与列表中一项一致。有未解决失败时记录failure并用insufficient。不得为通过校验补造已阅读记录。

这些是报告所需的轻量引用记录，不是标准全文档案。默认保留链接、引用信息和简短判断依据；阅读PDF或OCR所需文件放临时目录，阅读结束仅清理本次工具生成的临时文件。用户明确要求归档再保存全文或条文页，不因假设性风险自动改变保存偏好。过往已交付的测试资料不自动删除。

报告可由脚本校验以上记录的完整性与一致性；脚本不证明链接当前在线、发布身份真实、条文解释正确或人确实读过。每次实际审查仍应打开所引正文和公告核验。不得把“只保留链接”理解为“只看网页标题”。
