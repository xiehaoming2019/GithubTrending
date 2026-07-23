# GitHub Trending 中文日报

每天抓取 GitHub Trending，使用 GitHub REST API 补全项目资料，再由 AI 生成中文项目解读和 Markdown 日报。

当前 MVP 具备：

- 抓取每日 Trending 前 N 个仓库
- 提取今日新增 Star、总 Star、Fork、语言和简介
- 补充 Topics、License、README、更新时间等官方仓库数据
- 使用 OpenAI Responses API 生成结构化中文解读
- 未配置 AI 密钥时自动降级为基础摘要
- 保存原始快照和 Markdown 日报
- GitHub Actions 每天北京时间 08:23 自动运行

## 本地运行

项目只使用 Python 标准库，不需要安装依赖。需要 Python 3.11 或更高版本。

```powershell
py -3 -m github_trending_daily --limit 10
```

生成结果位于：

```text
reports/YYYY-MM-DD.md
data/snapshots/YYYY-MM-DD.json
```

### 启用 AI 解读

在当前 PowerShell 会话设置环境变量：

```powershell
$env:OPENAI_API_KEY="你的 API Key"
$env:OPENAI_MODEL="gpt-5.6-luna"
py -3 -m github_trending_daily --limit 10
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

定时任务会提交 `reports/` 和 `data/snapshots/` 的新增内容。原始 HTML 只用于当次排错，不会提交。

## 常用参数

```text
--limit 10             日报项目数量
--language python      只看某种编程语言
--no-ai                禁用 AI，生成基础摘要
--no-enrich            不调用 GitHub REST API
--source-html FILE     从本地 HTML 解析，便于测试
--output FILE          指定日报输出位置
--date YYYY-MM-DD      指定日报日期
```

## 下一阶段

- 增加 SQLite 历史库，识别首次上榜、连续上榜和排名变化
- 增加整份日报的“今日技术风向”二次编辑
- 生成 HTML 邮件
- 接入飞书、企业微信或邮件推送
- 为 Trending 页面结构变化增加失败通知

