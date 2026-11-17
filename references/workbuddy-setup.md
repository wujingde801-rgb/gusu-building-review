# WorkBuddy 安装与环境检查

## 安装
在 WorkBuddy 的「专家·技能·连接器」→「技能」→「添加技能」→「上传技能」选择完整 ZIP 包，安装后在「已安装」中启用。不同版本入口名称可能略有差异。
不要仅上传 SKILL.md：本技能必须连同 scripts、references、assets 使用。

## 首次运行
定位本技能实际安装目录。使用当前机器的 Python 3.10 或以上解释器运行 `scripts/check_environment.py`，查看 JSON。
- pypdf：生成 PDF 页码索引所需。
- Pillow 与 pdftoppm（Poppler）：使用 pdf_evidence.py 裁图所需，pdftoppm 不是 pip 包。
- curl：ccsn.py 读取公开标准网站所需。Windows 应使用真实 curl 程序，不是 PowerShell 的同名别名。
如缺少 Python 包，可在独立虚拟环境中用其 Python 执行 `-m pip install -r <技能目录>/requirements.txt`。不要改动系统 Python 或自动修改安全设置。
缺少 Poppler 时可用 WorkBuddy 已有 PDF/图像工具查看、截图并手工登记；缺少 curl 时改用浏览器打开网站。无法实际看图时仅整理文字线索，相关页记 unreadable/unseen，不输出已完成图纸审查。
缺少 Python 时可按同样证据流程手工维护台账，但必须标注未运行脚本校验，不能宣称完整功能可用。
使用当前会话的本地日期；项目输出保存在独立工作目录，原始文件不修改。

## 能力验收
1. 读取本技能 SKILL.md、模块清单和审查流程，说明实际加载路径。
2. 执行环境检查，并在独立临时目录运行 scripts/tests/test_online_review.py 合成数据测试；不能把它当成实际项目结论。
3. 用用户提供的无敏感测试 PDF 创建台账，实际查看至少一页，登记页码和观察，再生成带未审范围的报告。
4. 需要联网规范时实际检索、打开详情和全文、查看引用正文页；失败保持 insufficient。
5. 核验报告真实链接、未知身份、未看页及待人工复核标记。

本分享包不携带原作者本地知识库、项目 PDF、账户、密钥或个人路径配置。规范及项目材料由使用者合法提供，知识库默认新建，不代表继承原作者历史审查经验库。

官方安装说明：https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market
