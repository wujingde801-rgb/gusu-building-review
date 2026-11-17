# 姑苏建筑方案审查

面向苏州市姑苏区建筑改造、片区更新与历史建筑修缮活化方案的辅助审查技能，提供 WorkBuddy 使用说明、通用模板和辅助脚本。结果须人工专业复核，不替代施工图法定审查或结构鉴定。

## 同事安装与更新

1. 打开本仓库的 **Releases**，下载最新版 `gusu-building-review-workbuddy.zip`。
2. WorkBuddy → 专家·技能·连接器 → 技能 → 添加技能 → 上传技能，导入完整 ZIP 并启用。
3. 首次使用要求 WorkBuddy 阅读 `references/workbuddy-setup.md`，检查环境并用无敏感样例 PDF 验收。
4. 新版发布后仍使用同一下载入口。更新前备份自己修改过的技能文件；通过客户端导入新版，核对已安装技能版本及启用状态。覆盖/重复导入行为须按实际客户端确认。

[最新版发布页](https://github.com/wujingde801-rgb/gusu-building-review/releases/latest) · [固定下载地址](https://github.com/wujingde801-rgb/gusu-building-review/releases/latest/download/gusu-building-review-workbuddy.zip)

GitHub 更新不代表 WorkBuddy 已安装副本会自动升级；当前采用下载 ZIP 导入流程。

## 对 WorkBuddy 说

> 请使用 gusu-building-review 技能，先阅读 references/workbuddy-setup.md 并检查本机环境，再审查我上传的方案 PDF。保留源文件，逐页记录实际阅读范围，联网核验规范全文，明确未审项与待人工复核事项。缺少工具时如实说明。

## 当前验证状态

0.2.0：已同步区位保护与报批核查流程，Python 3.12 下五项原有回归检查与区位台账抽查通过。尚未完成 WorkBuddy 客户端成功安装和真实方案全流程验收。代码测试不证明看图、规范适用或专业判断正确。

完整脚本模式要求 Python 3.10+；PDF 索引需 pypdf，裁图需 Pillow 与 Poppler 的 pdftoppm，标准网站读取脚本需 curl。缺少工具时的降级边界见技能说明。联网标准应每次核验，不能把历史访问成功当作持续可用证明。

## 维护与发布

此仓库是对外分享版的维护源。在这里修改流程、脚本和模板，避免直接改 ZIP。维护过程见 [维护说明](MAINTAINING.md)。

- 修改：更新技能文件、VERSION、CHANGELOG.md。
- 检查打包：`python tools/package.py`，生成 ZIP 与 SHA256SUMS；检查失败不发版。
- 发布：推送与 VERSION 相符的 `v版本号` 标签，GitHub Actions 检查后创建 Release 并上传安装包。也可在 Actions 手动执行发布流程。
- 反馈：在 Issues 中描述客户端版本、现象和已脱敏截图，不上传真实项目、规范全文或个人信息。

## 资料与来源

本仓库只包含技能、通用模板及辅助脚本，不含原作者知识库、项目 PDF、账户或个人配置。规范和项目材料由使用者合法提供。参考项目及其许可见 references/provenance.md 与 references/upstream-MIT-LICENSE.txt；上游许可不代表第三方资料可任意分发。本仓库未额外授予新的开源许可。

[WorkBuddy 官方安装说明](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)
