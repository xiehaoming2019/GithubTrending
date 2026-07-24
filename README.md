# GitHub Trending ACG 日报

每天抓取 GitHub Trending，并从 GitHub Search 补充近期活跃的 ACG 创作工具，
经过 AI 筛选和 7 天去重后生成精简中文日报。

当前 MVP 具备：

- 默认检查每日 Trending 前 25 个仓库，日报最多收录 8 个
- 通过 ACG 雷达补充游戏、动画、剪辑、VTuber、语音等近期活跃项目
- 最近 7 天介绍过的项目默认跳过，热度显著上升时才重新收录
- 每期目标包含约 3 个“ACG 新发现”，Agent / Skills 最多 3 个
- 按相关性、Star 增速、项目新鲜度和分类多样性综合排序
- 项目卡片直接说明“能做什么”，减少技术特性堆砌
- 用 AI 批量判断项目相关性，失败时自动改用本地关键词规则
- 达不到标准时宁可少发，不用通用框架、数据库、金融或炒币项目凑数
- 提取今日新增 Star、总 Star、Fork、语言和简介
- 补充 Topics、License、README、更新时间等官方仓库数据
- 使用 OpenAI Responses API 生成结构化中文解读
- 未配置 AI 密钥时自动降级为基础摘要
- 同一天重复运行时复用已有 AI 摘要，避免重复费用和无意义提交
- 保存原始快照和 Markdown 日报
- 可通过 QQ 邮箱 SMTP 发送排版后的 HTML 日报
- 自动任务失败时单独向本人发送告警，不打扰日报好友收件人
- GitHub Actions 每天北京时间 08:23 自动运行

关注方向包括：

- AI Agent / Skills、游戏开发、动画、视频剪辑
- AI 绘画 / 漫画、AI 视频、3D / VTuber
- 语音 / 配音、音乐 / 音效、互动叙事
- XR / 虚拟制作、ACG 本地化、ACG 资源 / Mod、创作者自动化

## 本地运行

项目只使用 Python 标准库，不需要安装依赖。需要 Python 3.11 或更高版本。

```powershell
py -3 -m github_trending_daily --limit 8
```

生成结果位于：

```text
reports/YYYY-MM-DD.md
data/snapshots/YYYY-MM-DD.json
data/candidates/YYYY-MM-DD.json
```

### 启用 AI 解读

在当前 PowerShell 会话设置环境变量：

```powershell
$env:OPENAI_API_KEY="你的 API Key"
$env:OPENAI_MODEL="gpt-5.6-luna"
py -3 -m github_trending_daily --limit 8
```

`gpt-5.6-luna` 适合这种每日批量摘要场景；也可以通过 `OPENAI_MODEL` 换成账户可用的其他 Responses API 模型。

### GitHub API Token

公开仓库可以不带 Token 读取，但容易遇到较低的限流。本地建议设置：

```powershell
$env:GITHUB_TOKEN="你的 GitHub Token"
```

GitHub Actions 会自动使用仓库提供的 `GITHUB_TOKEN`。

### 离线检查

下面的命令使用测试夹具，不访问 GitHub，也不调用 AI：

```powershell
py -3 -m github_trending_daily `
  --source-html tests/fixtures/trending.html `
  --no-enrich `
  --no-ai `
  --no-interest-filter `
  --output reports/demo.md
```

运行测试：

```powershell
py -3 -m unittest discover -s tests -v
```

## 启用每日任务

1. 将仓库推送到 GitHub。
2. 在仓库 `Settings → Secrets and variables → Actions` 中新增 Secret：`OPENAI_API_KEY`。
3. 如需更换模型，新增 Variable：`OPENAI_MODEL`。
4. 确认 Actions 的 Workflow permissions 允许写入仓库内容。
5. 在 Actions 页面手动运行一次 `GitHub Trending Daily` 验证结果。

定时任务会提交 `reports/`、`data/snapshots/` 和 `data/candidates/` 的新增内容。
候选快照用于计算次日 Star 增速；原始 HTML 只用于当次排错，不会提交。

## QQ 邮箱推送

QQ 邮箱发送需要使用 SMTP 授权码，不能使用 QQ 登录密码：

1. 登录 QQ 邮箱网页版，进入“设置 → 账户”。
2. 开启 `POP3/SMTP` 或 `IMAP/SMTP` 服务。
3. 生成一个单独的 SMTP 授权码。
4. 在 GitHub 仓库 `Settings → Secrets and variables → Actions` 中添加：
   - `QQ_EMAIL`：完整发件邮箱，例如 `123456@qq.com`
   - `QQ_SMTP_AUTH_CODE`：刚生成的授权码
   - `EMAIL_TO`：收件邮箱；不设置时默认发给发件邮箱自己
   - `ALERT_EMAIL_TO`：可选的失败告警邮箱；不设置时只发给 `QQ_EMAIL` 本人

工作流使用 `smtp.qq.com:465` 的 SSL 连接。凭据不写入代码，缺少配置时会跳过邮件发送，但日报仍会正常生成。
测试、抓取、AI、邮件发送或 Git 提交任一阶段失败时，Actions 会尝试发送告警邮件；
告警失败不会掩盖原始任务错误，也不会发送给普通的 `EMAIL_TO` 好友列表。

本地测试发送：

```powershell
$env:QQ_EMAIL="你的QQ邮箱"
$env:QQ_SMTP_AUTH_CODE="你的SMTP授权码"
$env:EMAIL_TO="接收日报的邮箱"
python -m github_trending_daily --limit 8 --send-email
```

## 常用参数

```text
--limit 8              日报项目数量
--candidate-limit 25   筛选前检查的 Trending 候选数
--relevance-threshold 60  ACG / 创作者相关性最低分
--radar-candidate-limit 18  ACG 雷达候选数
--radar-limit 3        每期 ACG 新发现目标数
--history-days 7       项目去重天数
--language python      只看某种编程语言
--no-ai                禁用 AI，生成基础摘要
--no-interest-filter   禁用 ACG / 创作者相关性筛选
--no-radar             禁用 ACG 雷达
--no-deduplicate       禁用近期项目去重
--no-enrich            不调用 GitHub REST API
--send-email           已配置 SMTP 凭据时发送 HTML 邮件
--source-html FILE     从本地 HTML 解析，便于测试
--output FILE          指定日报输出位置
--date YYYY-MM-DD      指定日报日期
```

## 下一阶段

- 完善“突然升温”和跨日排名变化标记
- 增加整份日报的“今日 ACG 技术风向”二次编辑
- 接入飞书或企业微信推送
- 为 Trending 页面结构变化增加失败通知
