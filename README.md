# 刘莹 · 人力排期看板（Selene → 可视化）

把 **Selene 人力排期系统**的员工排期数据，自动生成为一份**自包含、可分享**的 HTML 看板，方便测试 / 研发 / 产品随时查看某位同事在未来一段时间内的任务排期、状态分布与工作量。

> 数据源：Selene 人力排期系统（`http://selene.hd123.cn:52163/selene-web/`）
> 看板风格：暖米极简配色，移动端 / PC 端自适应，无需后端、无数据库。

---

## 这个看板能做什么

- **一屏看全排期**：顶部 4 张统计卡（任务总数 / 已完成 / 进行中 / 未开始）+ 任务明细表格。
- **动态时间窗口**：打开看板时按「今天前 2 天 ~ 今天后 4 天」自动筛选，无需手动改日期。
- **状态一目了然**：任务按 Jira 状态着色（测试中 / 开发完成 / 开始 / 开发中 / 关闭 / 已解决）。
- **直达 Jira**：点击任意任务号，直接跳转公司 Jira 对应任务单。
- **产品耗时冠军**：在「产品」列表头下方标出当前窗口内耗时最多的产品。
- **工作量预警**：当前窗口工作量超过 40h 时，给出「已超负荷运作」提示。
- **移动端友好**：手机上卡片式展示、筛选标签、横幅均做了适配。

---

## 文件说明

| 文件 | 作用 |
|------|------|
| `gen_dashboard_v2.py` | 生成脚本：读取排期数据 JSON，输出看板 HTML |
| `fetch_selene.py` | 拉取脚本：调用 Selene API 拉取最新排期，写入 `gantt_live.json` 并重新生成看板 |
| `gantt_live.json` | 排期数据快照（由 `fetch_selene.py` 生成，含脱敏后的任务数据） |
| `刘莹_人力排期看板.html` | **最终看板**：直接用浏览器打开即可查看 |
| `deploy/index.html` | 对外分享用的部署副本（同最终看板） |
| `selene_token.txt` | Selene token（**已被 .gitignore 排除，不会提交**） |
| `setup_autosync.bat` | Windows 任务计划一键注册：每小时自动拉取 + 生成 |

---

## 如何运行（重新生成看板）

需要 Python 3.8+，在仓库目录下执行：

```bash
python gen_dashboard_v2.py
```

脚本读取同目录的 `gantt_live.json`，生成 `刘莹_人力排期看板.html`。
直接用浏览器打开该 HTML 即可查看，无需联网、无需登录。

---

## 如何拉取最新排期数据

看板数据默认是**静态快照**（`gantt_live.json`）。如需刷新到最新排期，用自动化脚本：

```bash
# token 来源：登录 Selene 网页 → DevTools → Application → Local Storage →
#   http://selene.hd123.cn:52163 → 复制 vuex 里的 token 字段
set SELENE_TOKEN=你的token        # 方式 A：环境变量
# 或把 token 写入同目录 selene_token.txt   # 方式 B：文件（勿提交到公开仓库）
python fetch_selene.py
```

`fetch_selene.py` 会从 Selene API 拉取「今天前 2 天 ~ 今天后 4 天」数据，保存为 `gantt_live.json` 并自动重新生成看板。

**每小时自动刷新（Windows 任务计划）**：双击运行 `setup_autosync.bat`，会用任务计划创建名为 `SeleneDashboardSync` 的每小时任务，自动执行 `fetch_selene.py`（拉取 + 生成 + 同步到 `deploy/`）。日志见 `selene_sync.log`。

> 注意：Selene token 会过期，过期后脚本会报错退出，需重新从浏览器取一次 token。

### 方式二：手动 curl（留档）

用已登录 Selene 的浏览器，从 LocalStorage 提取 `vuex` 中的 `token`，调用接口：

```bash
curl -X POST "http://selene.hd123.cn:52163/selene/v1/plan/gantt/employee/query" \
  -H "Authorization: <token>" \
  -H "x-requested-with: XMLHttpRequest" \
  -H "Content-Type: application/json" \
  -d '{"beginDate":"2026-08-13","endDate":"2026-08-19","departments":["测试二部"],"employees":["liuying"],"queryRef":false}' \
  -o gantt_live.json
```

> 注意：`Authorization` 头**不带** `Bearer` 前缀；`beginDate/endDate` 为查询窗口（前 2 天 → 后 4 天）。

---

## Token 更新 SOP（重要）

Selene 的 token 是 **JWT，有效期约 24 小时**，过期后接口返回 401/403。按以下步骤更新：

1. 用浏览器登录 Selene 网页（`http://selene.hd123.cn:52163/selene-web/`）。
2. 打开 DevTools → **Application** → **Local Storage** → `http://selene.hd123.cn:52163`。
3. 找到 `vuex`（或 `token`）字段，复制其中的 token 字符串。
4. 把新 token 写入 `selene_token.txt`（同目录，已被 .gitignore 排除，不会提交）。
   - 或直接设置环境变量：`set SELENE_TOKEN=新token`。
5. 运行 `python fetch_selene.py` 重新拉取并生成。
6. 若要看板对外分享链接也更新，请重新 deploy `deploy/index.html`。

---

## 部署与分享

- 本地：`浏览器直接打开 刘莹_人力排期看板.html`。
- 对外分享（线上托管）：已迁移到 **腾讯云开发 CloudBase 静态托管**，链接稳定、域名干净独立，不会被安全软件连带标记为危险网页：
  - **线上地址：`https://ordering-app-d9gxw51o637a01eed-1309857701.tcloudbaseapp.com/index.html`**
  - 该链接对应 `deploy/index.html`，由 `fetch_selene.py` 的 `deploy_cloudbase()` 推送到 CloudBase 环境 `ordering-app-d9gxw51o637a01eed`。
- 早期曾用 CloudStudio 免费沙箱，但其空闲回收会导致链接打不开、且共享二级域名 `*.app.workbuddy.link` 易被安全软件连同标记，故迁移至 CloudBase。

---

## 看板设计要点（已确认的需求）

- **数据窗口**：打开时按「今天前 2 天 ~ 今天后 4 天」动态筛选（数据窗口随打开日期后移）。
- **统计卡 4 个**：任务总数 / 已完成(关闭) / 进行中(测试中) / 未开始(开发完成+开发中+开始)，数字固定为窗口内全量，不随筛选变化。
- **过滤规则**：自动过滤 `MASK01`、`TM-` 开头的任务单（内部占位 / 模板单）。
- **默认勾选**：「测试中 + 开发完成」。
- **Jira 跳转**：任务号点击跳转 `http://jira6.app.hd123.cn/jira/browse/{任务号}`（PC 端新标签页，移动端同标签页打开，规避微信拦截）。
- **任务名称**：单行展示，超出省略，鼠标悬停显示完整。
- **开发人**：取「前置任务员工」姓名（`prev.employeeName`），更符合排期责任归属。
- **产品耗时冠军**：在「产品」列列表头下方标注当前窗口耗时最多的产品。
- **工作量预警**：窗口内总工作量 > 40h 时提示「已超负荷运作」。

## 自动化刷新方案

**本地每小时自动刷新（推荐）**：双击运行 `setup_autosync.bat`，会用 Windows 任务计划创建名为 `SeleneDashboardSync` 的每小时任务，自动执行 `fetch_selene.py`（拉取 + 生成 + 同步到 `deploy/`）。

**公开链接（CloudBase）自动更新**：`fetch_selene.py` 在重新生成看板后，会调用 `deploy_cloudbase()` 把 `deploy/` 推送到 CloudBase 静态托管。该步骤需要本机已安装并登录 `tcb` CLI（二者满足其一即可）：

```bash
# 方式 A：浏览器交互登录（本机执行一次，凭据会持久化）
tcb login
# 方式 B：用腾讯云永久密钥非交互登录（适合无人值守的定时任务）
tcb login --apiKeyId <SecretID> --apiKey <SecretKey>
```

登录后，每小时任务即可自动把最新看板推到 CloudBase，无需人工重新部署。若 `tcb` 未安装 / 未登录，`deploy_cloudbase()` 会优雅跳过（仅打印提示、不中断刷新），本地数据仍保持最新；此时需手动用 `tcb hosting deploy deploy -e ordering-app-d9gxw51o637a01eed` 推送一次。

> **全流程自动化卡点**：Selene token 需要浏览器登录态才能获取（自动登录受服务端 DTO 限制无法脚本化），目前无法做到「无人值守永久自动刷新」，必须每天人工复制一次 token。这是唯一需手动的环节。CloudBase 侧的推送凭据（tcb 登录）只需配置一次即可长期复用。
