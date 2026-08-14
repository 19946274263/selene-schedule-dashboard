# 刘莹 · 人力排期看板（Selene → 可视化）

把 Selene 人力排期系统的员工排期数据，生成为**自包含、可分享**的 HTML 看板。

## 文件说明

| 文件 | 作用 |
|------|------|
| `gen_dashboard_v2.py` | 生成脚本：读取排期数据 JSON，输出看板 HTML |
| `gantt_0814_0821.json` | 排期数据快照（2026-08-14 拉取，已脱敏，无 token） |
| `刘莹_人力排期看板.html` | **最终版**看板（抹茶绿配色、4 个统计卡、精简列） |
| `刘莹_人力排期看板_20260814.html` | 旧完整版（含甘特图/项目分布/状态分布，留档） |

## 如何运行（重新生成看板）

需要 Python 3.8+，在仓库目录下执行：

```bash
python gen_dashboard_v2.py
```

脚本会读取同目录的 `gantt_0814_0821.json`，在同目录生成 `刘莹_人力排期看板.html`。
直接用浏览器打开该 HTML 即可查看，无需联网、无需登录。

## 如何拉取最新排期数据

看板数据默认是**静态快照**（`gantt_0814_0821.json`）。如需刷新到最新排期，推荐用自动化脚本：

### 方式一：自动脚本（推荐，支持每小时刷新）

`fetch_selene.py` 会从 Selene API 拉取「今天 ~ 今天+7 天」数据，保存为 `gantt_live.json` 并自动重新生成看板。

```bash
# token 来源：登录 Selene 网页 → DevTools → Application → Local Storage →
#   http://selene.hd123.cn:52163 → 复制 vuex 里的 token 字段
set SELENE_TOKEN=你的token        # 方式 A：环境变量
# 或把 token 写入同目录 selene_token.txt   # 方式 B：文件（勿提交到公开仓库）
python fetch_selene.py
```

看板底部「当前查看窗口」处会显示**最近获取**时间（来自数据里的 `fetchTime`）。

**每小时自动刷新（Windows 任务计划）**：

```bat
schtasks /create /sc hourly /tn "SeleneDashboardSync" /tr "python C:\...\selene-schedule-dashboard\fetch_selene.py"
```

> 注意：Selene token 会过期，过期后脚本会报错退出，需重新从浏览器取一次 token。

### 方式二：手动 curl（留档）

用已登录 Selene 的浏览器，从 LocalStorage 提取 `vuex` 中的 `token`，调用接口：

```bash
curl -X POST "http://selene.hd123.cn:52163/selene/v1/plan/gantt/employee/query" \
  -H "Authorization: <token>" \
  -H "x-requested-with: XMLHttpRequest" \
  -H "Content-Type: application/json" \
  -d '{"beginDate":"2026-08-14","endDate":"2026-08-21","departments":["测试二部"],"employees":["liuying"],"queryRef":false}' \
  -o gantt_0814_0821.json
```

> 注意：`Authorization` 头**不带** `Bearer` 前缀；`beginDate/endDate` 为查询窗口。
> 替换上面的日期即可拉取不同窗口的排期。

3. 重新运行 `python gen_dashboard_v2.py` 生成看板。

## 看板设计要点（已确认的需求）

- 打开时按「当天 ~ 当天+7天」动态筛选显示（数据窗口随打开日期后移）。
- 统计卡 4 个：**任务总数 / 已完成(关闭) / 进行中(测试中) / 未开始(开发完成+开发中+开始)**，数字固定为窗口内全量，不随筛选变化。
- 过滤 `MASK01`、`TM-` 开头的项目单。
- 默认勾选「测试中 + 开发完成」。
- 任务号点击跳转 Jira：`http://jira6.app.hd123.cn/jira/browse/{任务号}`（新标签页打开）。
- 摘要 / 客户项目超一行省略，悬停显示完整；开始 / 产品列完整展示；无「截止」列。

## 数据窗口说明

`gantt_0814_0821.json` 抓取于 2026-08-14，覆盖 08-14~08-21。
看板里「7 天窗口」只是按打开当天**重新筛选这份快照**，并不会自动联网拉新数据。
若需长期有效，需按上面步骤定期重新拉取数据并重生成（可做成定时任务）。
