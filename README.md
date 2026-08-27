# 刘莹 · 人力排期看板（Selene → 可视化）

把 Selene 人力排期系统的员工排期数据，做成**可分享的 HTML 看板**。共有两个版本：

- **离线版**（本地）：`刘莹_人力排期看板.html`，数据内嵌，无需联网、无需登录，发给任何人直接打开。
- **在线版**（云）：部署在 CloudBase 上的实时看板，打开时通过服务端代理 `seleneProxy` 实时拉取 Selene 数据（前端不直接暴露 token、不受跨域限制）。

## 文件说明

| 文件 | 作用 |
|------|------|
| `gen_dashboard_v2.py` | 生成脚本（离线版唯一真相源）：读取排期数据 JSON，输出看板 HTML |
| `gantt_0825_0907.json` | 离线快照（2026-08-25 拉取，窗口 08-25~09-07，已脱敏，无 token） |
| `刘莹_人力排期看板.html` | **离线版**最终看板（抹茶绿配色、4 个统计卡、精简列，数据内嵌） |
| `刘莹_人力排期看板_20260814.html` | 旧完整版（含甘特图/项目分布/状态分布，留档） |
| `selene_token.txt` | **切勿提交**：Selene JWT token（约 24h 过期），仅供本地刷新数据用 |
| `cloudbaserc.json` | **切勿提交**：含云函数环境变量 `SELENE_TOKEN`，用于轮换 token |
| `fn_seleneProxy/` | **切勿提交**：`seleneProxy` 云函数代码（本地副本，供 `tcb fn deploy` 使用） |
| `cloud_check.html` | **切勿提交**：线上 `index.html` 的本地工作副本（含内嵌 `let D` 快照 + 自动 `loadLive()`），是静态页部署源。改完此处再 `tcb hosting deploy` 才生效 |

> `.gitignore` 已排除 `selene_token.txt`、`cloudbaserc.json`、`fn_seleneProxy/`，避免把 token 推到公开仓库。

## 本地：刷新并重新生成离线版

需要 Python 3.8+，在仓库目录下执行：

```bash
python gen_dashboard_v2.py
```

脚本读取同目录的 `gantt_0825_0907.json`，生成 `刘莹_人力排期看板.html`（sprint 标签会根据数据日期自动计算，无需手改）。

### 拉取最新排期快照（覆盖 gantt_0825_0907.json）

1. 用已登录 Selene 的浏览器，从 LocalStorage 提取 `vuex` 中的 `token`
   （Selene 地址：`http://selene.hd123.cn:52163/selene-web/`），写入 `selene_token.txt`。
2. 调接口（注意 `Authorization` 头**不带** `Bearer`，`beginDate/endDate` 为查询窗口）：

```bash
TOKEN=$(cat selene_token.txt | tr -d '\n\r')
curl -s -X POST "http://selene.hd123.cn:52163/selene/v1/plan/gantt/employee/query" \
  -H "Authorization: $TOKEN" \
  -H "x-requested-with: XMLHttpRequest" \
  -H "Content-Type: application/json" \
  -d '{"beginDate":"2026-08-25","endDate":"2026-09-07","departments":["测试二部"],"employees":["liuying"],"queryRef":false}' \
  -o gantt_0825_0907.json
```

3. 重新运行 `python gen_dashboard_v2.py`。

## 部署到云（在线版，CloudBase）

环境：`ordering-app-d9gxw51o637a01eed`（ap-shanghai）。已安装并登录 `tcb` CLI。

- **静态看板**（`index.html`，实时版）：`tcb hosting deploy <本地index.html路径> index.html -e ordering-app-d9gxw51o637a01eed`
- **服务端代理**（`seleneProxy` 云函数）：持有 `SELENE_TOKEN` 环境变量，代理请求 Selene，
  查询窗口为「今天 ±21 天」，前端按所选周期子窗口过滤。**带 60s 内存缓存**：同一云函数实例在 60s 内复用一次拉取结果，显著降低多人同时打开时的 Selene 调用压力（命中时响应含 `cached:true`，`lastFetch` 保留数据实际拉取时间）。
  访问地址：`https://ordering-app-d9gxw51o637a01eed.service.tcloudbase.com/seleneProxy`

### 轮换 token（约 24h 过期，需定期做）

token 在云函数环境变量里，**不在** `index.html` 中。步骤：

1. 把新 token 写入 `cloudbaserc.json` 的 `functions[0].envVariables.SELENE_TOKEN`。
2. 部署函数（**不要加 `--httpFn`**，否则会变成 Web 函数、破坏现有 HTTP 访问；保持 Event 函数 + HTTP 访问）：

```bash
tcb fn deploy seleneProxy --dir fn_seleneProxy -e ordering-app-d9gxw51o637a01eed
```

3. 验证：访问上面 `seleneProxy` 地址，返回 JSON 中 `tokenExpired` 应为 `false`，`tokenExp` 应为新过期时间。

4. **（推荐，顺手做）刷新首屏内嵌快照**：函数部署后代理已返回最新数据，但静态页内嵌的 `let D` 还是上次的旧快照，首屏会先闪旧数据再被自动 `loadLive()` 覆盖。把 `cloud_check.html` 的内嵌 `let D` 替换为代理当前最新数据，再部署静态页，首屏即是最新：

```bash
# 拉最新数据
curl -s "https://ordering-app-d9gxw51o637a01eed.service.tcloudbase.com/seleneProxy" -o latest.json
# 用括号计数精确替换 cloud_check.html 中 let D = {...} 大对象（变量名 let D，勿简单正则）
python - <<'PY'
import json
h=open('cloud_check.html',encoding='utf-8').read()
data=json.load(open('latest.json',encoding='utf-8'))
i=h.find('let D ='); s=h.find('{',i); d=0; e=-1
for j in range(s,len(h)):
    if h[j]=='{':d+=1
    elif h[j]=='}':
        d-=1
        if d==0:e=j;break
json.loads(h[s:e+1])  # 确认旧块合法
h2=h[:s]+json.dumps(data,ensure_ascii=False)+h[e+1:]
open('cloud_check.html','w',encoding='utf-8').write(h2)
PY
# 部署静态页
tcb hosting deploy cloud_check.html index.html -e ordering-app-d9gxw51o637a01eed
```

> 若只是轮换 token、没动 `cloud_check.html`，首屏会短暂显示旧快照（自动 `loadLive()` 会覆盖，不影响正确性）；若想首屏直接最新，照上面第 4 步做。

### 更新内嵌快照（首屏即最新）

线上 `index.html` 初次加载先渲染内嵌的 `let D = {...}` 快照，再自动 `loadLive()` 覆盖为实时数据。为避免首屏先闪旧快照，部署静态页前应先把内嵌 `let D` 替换为代理当前最新数据：

1. 拉取代理当前数据：`curl -s "https://ordering-app-d9gxw51o637a01eed.service.tcloudbase.com/seleneProxy" -o latest.json`
2. 用脚本把 `latest.json` 内容替换 `index.html` 里 `let D = {...}` 的大对象（注意变量名是 `let D`，需用括号计数精确定位，不能简单正则）。
3. 再部署：`tcb hosting deploy <本地index.html> index.html -e ordering-app-d9gxw51o637a01eed`

> 若跳过此步直接部署，首屏会回到上次部署时的旧快照（自动 `loadLive()` 仍会覆盖，但会有一次闪动）。

## 看板设计要点（已确认的需求）

- 离线版打开时按「当天 ~ 当天+7天」动态筛选显示（数据窗口随打开日期后移）。
- 统计卡 4 个：**任务总数 / 已完成(关闭) / 进行中(测试中) / 未开始(开发完成+开发中+开始)**。
- 过滤 `MASK01`、`TM-` 开头的项目单。
- 默认勾选「测试中 + 开发完成」。
- 任务号点击跳转 Jira：`http://jira6.app.hd123.cn/jira/browse/{任务号}`（新标签页打开）。
- 摘要 / 客户项目超一行省略，悬停显示完整；开始 / 产品列完整展示；无「截止」列。

## 数据窗口说明

- 离线版 `gantt_0825_0907.json` 抓取于 2026-08-25，覆盖 08-25~09-07；看板里「7 天窗口」只是按打开当天重新筛选这份快照。
- 在线版由 `seleneProxy` 实时拉取「今天 ±21 天」，无需手动刷新快照。
- 若 token 过期，在线版会提示「token 已过期，请联系管理员更新 token」，按上面的轮换步骤处理即可。
