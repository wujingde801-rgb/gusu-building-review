# 独立本地知识库

## 存储与四层职责

SQLite负责目录、历史、提案、审计；文件夹负责原文。四层为元数据分类，不强制移动用户既有目录。

| layer | 职责 | 可否单独支撑强制性结论 |
|---|---|---|
| A | 审查要点、结构化原子规则 | 否，必须关联B |
| B | 正式规范、法规、政策原文 | 需版本、有效性、适用性与措辞校验 |
| C | 官方答疑、技术解释、研究辅助 | 否，需辨识法定效力与正文关系 |
| D | 经用户确认的案例、审查经验 | 否，须回到本项目事实与B |

空层记录unavailable，不为了“四层齐全”填入无关资料。不要把其它城市的技术规定默认用于姑苏。

```text
独立知识库/
  catalog.sqlite       正式目录与历史、提案及确认审计
  originals/<sha256>   原始字节，不覆盖；文件名保存在元数据
  pending/<id>/        新原文与可读提案；不进入正式检索
  archive/             被替换/更新记录的历史元数据
  exports/             备份临时快照
```

status：unverified待核实；effective已核实有效；future尚未实施；repealed废止；superseded被替代；archived移出使用。新资料默认 unverified；元数据模板不暗示已核验。

相同SHA-256拒绝重复入库；同标题不同字节仍需比对版本，不能自动合并。replace 为同记录新修订，旧原文及元数据保留，默认检索只看最新修订；不同文号的新规范可新建记录，并对旧记录提案status=superseded及关联ID。

## 自然语言到操作

新增资料 → 读原文、识别元数据、判断layer/kind/地区/专业/状态；使用 `propose add` 暂存并展示具体变更。未识别日期用null，不能填当天替代发布日期。

确认 → 展示提案ID、摘要token、文件名/哈希、元数据、原版本/新版本及影响，用户明确确认后执行 apply，confirmation 保存实际回复原文或消息标识。token绑定提案内容，不能把生成token当成用户同意；脚本不具备身份鉴别能力，交互由WorkBuddy遵守。

“删除资料” → 默认 archive，可恢复且退出引用。永久删除原文会破坏既有报告证据链，V1不提供物理删除。需恢复时 metadata 提案改回 appropriate status 并重新核验。

更新/归档会使旧依据revision或状态变化，旧审查报告不能沿用已通过校验。数据库有写锁与预期revision检查，陈旧提案不能覆盖新变更。

## 命令（由WorkBuddy执行）

```sh
python scripts/kb.py --root /绝对路径/知识库 init
python scripts/kb.py --root /绝对路径/知识库 propose add --file /资料.pdf --metadata /元数据.json --text-file /可检索文本.txt
python scripts/kb.py --root /绝对路径/知识库 apply 提案ID --token 摘要token --confirmation '用户实际确认原文或消息标识'
python scripts/kb.py --root /绝对路径/知识库 search 无障碍
python scripts/kb.py --root /绝对路径/知识库 search 消防 --all
python scripts/kb.py --root /绝对路径/知识库 propose replace --record 记录ID --file /新版.pdf --metadata /新版元数据.json
python scripts/kb.py --root /绝对路径/知识库 propose metadata --record 记录ID --metadata /更正元数据.json
python scripts/kb.py --root /绝对路径/知识库 propose archive --record 记录ID
python scripts/kb.py --root /绝对路径/知识库 history 记录ID
python scripts/kb.py --root /绝对路径/知识库 backup /库外路径/知识库备份.zip
```

默认search仅返回B层、effective、已到实施日期、未到失效日、最近90天已核验的正式依据。查A/C/D及待核实资料使用 --all，人工筛选 layer、region、topics、kind；默认过滤不是法律适用结论。中文采用Unicode子串检索，无需向量库。Markdown/TXT/JSON/CSV自动索引；PDF/DOCX保留原文，用 --text-file 添加提取文本/OCR旁车，不提供旁车时只检索元数据。扫描件文本空不代表无规定；旁车仅定位，引用必须回到原文页。

元数据可追加发布日期、文号、用途、阶段、保护类型、地区、上/下位关联及supersedes，不认识的字段原样保留。每次变更必须提供完整元数据，避免隐式补值。

备份使用SQLite一致性快照，包含原文、提案和档案；恢复到新空目录解压后运行search --all并抽查原文哈希，不覆盖现有库。原始入库目录及备份可能含敏感资料，不上传公共仓库。

## 线上标准与本地补充的分工

用户默认线上标准为主，本地维护地方正式资料、审查要点及项目经验。已核验线上正文可按review.json的online依据独立参与审查，不要求先正式入库；规范全文不默认长期保存。四层职责仍适用于证据性质，不表示所有B类原文必须存在本地数据库。正式本地库变更仍走原有提案确认，线上项目引用记录不属于正式知识库变更。
