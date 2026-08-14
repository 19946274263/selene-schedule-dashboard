# -*- coding: utf-8 -*-
"""生成刘莹人力排期看板 HTML — 暖米极简工程师风

变更记录：
- 静态快照也显示 HTML 生成时间
- 列宽：产品列收窄，客户项目列加宽
- 移动端重写：标题不竖排、状态标签不竖排、表格改为卡片列表、取消纵向滚动、消除滚动晃动
- 任务明细底部去重线
- 最后一条数据后增加俏皮提示语
- 增强缺省/错误提示
"""
import json, os, datetime
from collections import Counter

TEMP = os.environ.get('TEMP', '')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '刘莹_人力排期看板.html')

# 数据源：优先读取实时拉取的快照，回退到同目录/系统 TEMP 的静态快照
_src_candidates = [
    os.path.join(HERE, 'gantt_live.json'),
    os.path.join(HERE, 'gantt_0814_0821.json'),
    os.path.join(TEMP, 'gantt_0814_0821.json'),
]
_src = next((p for p in _src_candidates if os.path.exists(p)), _src_candidates[-1])
d = json.load(open(_src, encoding='utf-8'))
data = d['data']
emp = data['employees'][0]
tasks_raw = emp['tasks']

def to_iso(s):
    if not s:
        return None
    return s[:10]

# 过滤 MASK01 + TM + 简化
simplified = []
for t in tasks_raw:
    key = t.get('key', '')
    if key.startswith('MASK01') or key.startswith('TM-'):
        continue
    k = to_iso(t.get('ganttKickoffDate') or t.get('kickoffDate'))
    e = to_iso(t.get('ganttDueDate') or t.get('dueDate'))
    simplified.append({
        'key': key,
        'summary': t.get('summary', ''),
        'status': t.get('status', ''),
        'progress': round((t.get('progress') or 0) * 100),
        'workload': t.get('workload') or 0,
        'kickoff': k or '',
        'due': e or '',
        'done': bool(t.get('done', False)),
        'product': t.get('product', ''),
        'proj': t.get('customerProject', ''),
        'starter': t.get('starterName', ''),
    })

# 按时间先后排序（kickoff 升序，due 升序）
simplified.sort(key=lambda x: (x['kickoff'] or '9999', x['due'] or '9999', x['key']))

# 工作量与产品分布统计
total_workload = round(sum(t['workload'] for t in simplified), 1)
overload = total_workload > 40
prod_wl = {}
for t in simplified:
    pr = t['product'].strip() or '未分类'
    prod_wl[pr] = prod_wl.get(pr, 0.0) + t['workload']
def short_name(p):
    """产品简称：取最后一个纯 ASCII 段（即中文名前的具体产品码）。
    例：sop-门店运营平台 -> sop；sy-dj-海鼎到家 -> dj"""
    parts = p.split('-')
    ascii_parts = [x for x in parts if x and not any('\u4e00' <= c <= '\u9fff' for c in x)]
    return ascii_parts[-1] if ascii_parts else p[:4]
prod_dist = sorted([{'product': p, 'hours': round(h, 1), 'short': short_name(p)} for p, h in prod_wl.items()], key=lambda x: -x['hours'])
for item in prod_dist:
    item['pct'] = round(item['hours'] / total_workload * 100, 1) if total_workload else 0
print("过滤后状态分布:", dict(Counter(t['status'] for t in simplified)))
print("数据源:", _src)
print("总工作量:", total_workload, "h 超负荷:", overload)
print("产品分布:", prod_dist)

# 静态快照也显示生成时间（不附加括号提示）
last_fetch = d.get('fetchTime')
if not last_fetch:
    last_fetch = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

payload = {
    'empName': emp.get('employeeName', ''),
    'empId': emp.get('employee', ''),
    'dept': emp.get('department', ''),
    'sprint': '0814~0821',
    'sprintBegin': data.get('beginDate', '')[:10],
    'sprintEnd': data.get('endDate', '')[:10],
    'lastFetch': last_fetch,
    'tokenExp': d.get('tokenExp', ''),
    'tokenExpired': d.get('tokenExpired', False),
    'totalWorkload': total_workload,
    'overload': overload,
    'productDist': prod_dist,
    'tasks': simplified,
}
data_json = json.dumps(payload, ensure_ascii=False)

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>刘莹 · 人力排期看板</title>
<style>
:root{
  --bg:#FCFAF7;
  --txt:#3A3835;
  --sub:#7A756F;
  --line:#E4E0DA;
  --divider:#ECE8E2;
  --head-bg:#F4F1EC;
  --head-txt:#5C5853;
  --row-bg:#FFFFFF;
  --row-hover:#F9F5EF;

  --warn-bg:#FBEFE6;--warn-txt:#9A4A1E;--warn-bd:#EBC9AE;

  --c-total-bg:#F1EDE8;--c-total-txt:#3A3835;
  --c-done-bg:#E2EFDE; --c-done-txt:#2F472A;
  --c-run-bg:#F8EAD8;  --c-run-txt:#614C2E;
  --c-wait-bg:#EDEAE5; --c-wait-txt:#54504B;

  --filter-bg:#F8F5F0;
  --search-bg:#FFFFFF;
  --btn-bg:#FFFFFF;
  --btn-border:#D9D4CD;

  --st-test-bg:#E6EFF6;--st-test-txt:#2C6CA3;--st-test-bd:#A9CCE6;--st-test-ac:#7FB2DA;
  --st-start-bg:#EFE7DA;--st-start-txt:#8A7250;--st-start-bd:#D8CBB6;--st-start-ac:#BBA37C;
  --st-dev-bg:#F1E0D3;--st-dev-txt:#9A5B36;--st-dev-bd:#E0C0A8;--st-dev-ac:#C98A5E;
  --st-done2-bg:#FBF0CE;--st-done2-txt:#8A630B;--st-done2-bd:#EAD08A;--st-done2-ac:#D9B85E;
  --st-close-bg:#E4EBDD;--st-close-txt:#4F6342;--st-close-bd:#CAD6BE;--st-close-ac:#8AA877;

  --p-test:#E6EFF6;--pf-test:#7FB2DA;
  --p-start:#EFE7DA;--pf-start:#BBA37C;
  --p-dev:#F1E0D3;--pf-dev:#C98A5E;
  --p-done2:#FBF0CE;--pf-done2:#D9B85E;
  --p-close:#E4EBDD;--pf-close:#8AA877;
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow-x:hidden}
body{background:var(--bg);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;padding:24px;line-height:1.5;min-width:0}
.wrap{max-width:1440px;margin:0 auto}

.head{background:#F4F1EC;border:1px solid var(--line);border-radius:8px;padding:22px 28px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.head .avatar{width:46px;height:46px;border-radius:50%;background:var(--c-total-bg);color:var(--c-wait-txt);display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:600;flex-shrink:0}
.head .title-wrap{flex:1;min-width:0}
.head h1{font-size:22px;font-weight:700;color:var(--txt);letter-spacing:.3px;word-break:keep-all;overflow-wrap:normal}
.head .meta{font-size:13px;color:var(--sub);margin-top:6px;word-break:keep-all}
.head .badge{background:#fff;border:1px solid var(--line);border-radius:999px;padding:9px 15px;font-size:13px;color:var(--sub);font-weight:500;flex-shrink:0}
.head .tagline{font-size:12px;color:var(--sub);margin-top:5px;opacity:.88;display:flex;align-items:center;gap:5px}
.head .tagline::before{content:"";width:14px;height:1px;background:var(--c-wait-txt);opacity:.5}

/* 顶部指标卡片 */
.cards{display:grid;grid-template-columns:repeat(5,1fr);gap:20px;margin:20px 0}
.card{border-radius:8px;padding:20px 22px;text-align:center;border:1px solid var(--line);cursor:pointer;transition:filter .15s,border-color .15s;user-select:none}
.card:hover{filter:brightness(.96)}
.card.active{border:2px solid #C9BBA8}
.card .num{font-size:34px;font-weight:800;line-height:1.1}
.card .lbl{font-size:12px;margin-top:8px;font-weight:600;line-height:1.35}
.card .ctip{font-size:11px;margin-top:7px;font-weight:500;line-height:1.4;opacity:.92;display:flex;align-items:center;gap:4px}
.card-total{background:var(--c-total-bg)} .card-total .num,.card-total .lbl{color:var(--c-total-txt)}
.card-done{background:var(--c-done-bg)} .card-done .num,.card-done .lbl{color:var(--c-done-txt)}
.card-run{background:var(--c-run-bg)} .card-run .num,.card-run .lbl{color:var(--c-run-txt)}
.card-wait{background:var(--c-wait-bg)} .card-wait .num,.card-wait .lbl{color:var(--c-wait-txt)}
.card-prod{background:var(--head-bg)} .card-prod .num,.card-prod .lbl{color:var(--head-txt)}
.card-prod .ctip{flex-direction:column;align-items:center;gap:2px}
.prod-bars{height:5px;border-radius:3px;overflow:hidden;display:flex;width:100%;margin-top:4px;max-width:120px;margin-left:auto;margin-right:auto}
.prod-seg{height:100%}
.prod-legend{display:flex;flex-wrap:wrap;justify-content:center;gap:4px 8px;font-size:10px;color:var(--sub);margin-top:5px}
.prod-legend i{display:inline-block;width:6px;height:6px;border-radius:2px;margin-right:2px}

.panel{background:#fff;border-radius:8px;padding:24px 28px;border:1px solid var(--line)}
.panel h2{font-size:17px;font-weight:700;margin-bottom:16px;display:flex;align-items:center;gap:8px;color:var(--txt)}
.panel h2::before{content:"";width:5px;height:18px;background:var(--c-wait-txt);border-radius:3px}
.window-info{font-size:13px;color:var(--sub);margin-bottom:18px;background:var(--filter-bg);border-radius:8px;padding:12px 16px;border:1px solid var(--line);display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.window-info .win-main{flex:1;min-width:0}
.window-info .win-fetch{margin-left:auto;white-space:nowrap}
.window-info b{color:var(--txt)}

/* 筛选栏 */
.filters{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;align-items:center;
  background:var(--filter-bg);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.filters input{padding:9px 14px;border:1px solid var(--btn-border);border-radius:8px;font-size:13px;background:var(--search-bg);color:var(--txt);outline:none;transition:border-color .2s,box-shadow .2s;width:300px}
.filters input:focus{border-color:#C9BBA8;box-shadow:0 0 0 3px rgba(201,187,168,.18)}
.chk-group{display:flex;gap:8px;flex-wrap:wrap}
.chk{display:inline-flex;align-items:center;gap:8px;padding:7px 14px;border:1px solid var(--btn-border);border-radius:8px;font-size:13px;cursor:pointer;user-select:none;transition:all .15s;background:var(--btn-bg);color:var(--sub)}
.chk input{width:15px;height:15px;margin:0;cursor:pointer;flex-shrink:0}
.chk span{white-space:nowrap}
.chk:hover{border-color:#C9BBA8}
.chk.s-test:has(input:checked){background:var(--st-test-bg);border-color:var(--st-test-bd);color:var(--st-test-txt);font-weight:600}
.chk.s-test:has(input:checked) input{accent-color:var(--st-test-ac)}
.chk.s-start:has(input:checked){background:var(--st-start-bg);border-color:var(--st-start-bd);color:var(--st-start-txt);font-weight:600}
.chk.s-start:has(input:checked) input{accent-color:var(--st-start-ac)}
.chk.s-dev:has(input:checked){background:var(--st-done2-bg);border-color:var(--st-done2-bd);color:var(--st-done2-txt);font-weight:600}
.chk.s-dev:has(input:checked) input{accent-color:var(--st-done2-ac)}
.chk.s-dev2:has(input:checked){background:var(--st-dev-bg);border-color:var(--st-dev-bd);color:var(--st-dev-txt);font-weight:600}
.chk.s-dev2:has(input:checked) input{accent-color:var(--st-dev-ac)}
.chk.s-done:has(input:checked){background:var(--st-close-bg);border-color:var(--st-close-bd);color:var(--st-close-txt);font-weight:600}
.chk.s-done:has(input:checked) input{accent-color:var(--st-close-ac)}
.reset-btn{padding:9px 16px;border:1px solid var(--warn-bd);border-radius:8px;font-size:13px;background:var(--warn-bg);color:var(--warn-txt);cursor:pointer;transition:all .15s;font-weight:600;margin-left:auto}
.reset-btn:hover{background:#F3E4D6;color:#7A3A15}
.filters .hint{font-size:12px;color:var(--sub);margin-left:0}

/* 表格：固定布局 */
.tbl-wrap{overflow:auto;border:1px solid var(--line);border-radius:8px}
table{width:100%;border-collapse:collapse;font-size:12.5px;min-width:1000px;table-layout:fixed}
thead th{position:sticky;top:0;background:var(--head-bg);z-index:2;text-align:left;padding:13px 12px;font-weight:600;color:var(--head-txt);border-bottom:1px solid var(--line);white-space:nowrap}
tbody td{padding:14px 12px;border-bottom:1px solid var(--divider);vertical-align:middle;background:var(--row-bg);overflow:hidden}
tbody tr{cursor:pointer;transition:background .12s}
tbody tr:hover{background:var(--row-hover)}
tbody tr:last-child td{border-bottom:none}
.cell{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nowrap{white-space:nowrap}
.key a{color:var(--wait-txt);font-weight:600;white-space:nowrap;text-decoration:none;border-bottom:1.5px dashed transparent;transition:all .2s}
.key a:hover{color:#7a5a30;border-bottom-color:#7a5a30}
.tag{display:inline-block;padding:3px 10px;border-radius:6px;font-size:11px;font-weight:600;white-space:nowrap;transition:filter .15s}
.tag:hover{filter:brightness(.95)}
.tag-run{background:var(--st-test-bg);color:var(--st-test-txt)}
.tag-start{background:var(--st-start-bg);color:var(--st-start-txt)}
.tag-dev{background:var(--st-dev-bg);color:var(--st-dev-txt)}
.tag-wait{background:var(--st-done2-bg);color:var(--st-done2-txt)}
.tag-done{background:var(--st-close-bg);color:var(--st-close-txt)}

/* 进度列 */
.prog{display:flex;flex-direction:column;gap:5px}
.prog-pct{font-size:12px;font-weight:600;color:var(--txt);font-variant-numeric:tabular-nums}
.prog-bar{height:5px;border-radius:3px;overflow:hidden}
.prog-fill{height:100%;border-radius:3px}
.p-test{background:var(--p-test)} .pf-test{background:var(--pf-test)}
.p-start{background:var(--p-start)} .pf-start{background:var(--pf-start)}
.p-dev{background:var(--p-dev)} .pf-dev{background:var(--pf-dev)}
.p-done2{background:var(--p-done2)} .pf-done2{background:var(--pf-done2)}
.p-close{background:var(--p-close)} .pf-close{background:var(--pf-close)}

.mono{font-variant-numeric:tabular-nums}
.empty{text-align:center;padding:48px 20px;color:var(--sub);font-size:14px;line-height:1.8}
.empty .em{font-size:30px;display:block;margin-bottom:8px;opacity:.6}
.foot{margin-top:18px;text-align:center;color:var(--sub);font-size:12px}
.foot span{color:var(--c-run-txt);font-weight:500}

/* 侧边详情弹窗 */
.drawer{position:fixed;inset:0;z-index:50;visibility:hidden;pointer-events:none}
.drawer.open{visibility:visible;pointer-events:auto}
.drawer-mask{position:absolute;inset:0;background:rgba(58,56,53,.28);opacity:0;transition:opacity .2s}
.drawer.open .drawer-mask{opacity:1}
.drawer-panel{position:absolute;top:0;right:0;height:100%;width:380px;max-width:88vw;background:var(--bg);
  border-left:1px solid var(--line);box-shadow:-6px 0 20px rgba(58,56,53,.08);
  transform:translateX(100%);transition:transform .25s ease;display:flex;flex-direction:column}
.drawer.open .drawer-panel{transform:translateX(0)}
.drawer-head{display:flex;align-items:center;justify-content:space-between;padding:18px 22px;border-bottom:1px solid var(--line);background:#F4F1EC}
.drawer-title{font-size:15px;font-weight:700;color:var(--txt)}
.drawer-close{border:none;background:transparent;font-size:22px;line-height:1;color:var(--sub);cursor:pointer;padding:0 4px}
.drawer-close:hover{color:var(--txt)}
.drawer-body{padding:20px 22px;overflow:auto;flex:1}
.dl{display:flex;flex-direction:column;gap:14px}
.dl .row{display:flex;flex-direction:column;gap:4px}
.dl .k{font-size:12px;color:var(--sub)}
.dl .v{font-size:13.5px;color:var(--txt);line-height:1.5;word-break:break-word}
.dl .v a{color:var(--wait-txt);text-decoration:none;font-weight:600;border-bottom:1.5px dashed transparent}
.dl .v a:hover{border-bottom-color:var(--wait-txt)}
.dl hr{border:none;border-top:1px solid var(--divider);margin:2px 0}

/* 合并的任务列 */
.task-cell{display:flex;flex-direction:column;gap:3px}
.task-key{color:var(--wait-txt);font-weight:600;white-space:nowrap;text-decoration:none;border-bottom:1.5px dashed transparent;cursor:pointer;transition:all .2s;width:fit-content}
.task-key:hover{color:#7a5a30;border-bottom-color:#7a5a30}
.task-name{color:#A8A29C;font-size:11.5px;line-height:1.4;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}

/* 顶部俏皮提示语 */
.tip{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--c-run-txt);background:var(--c-run-bg);border:1px solid #EAD9C0;border-radius:8px;padding:9px 14px;margin-bottom:14px}
.tip .em{font-size:15px}
/* 弱化版提示语（置于窗口信息上方，视觉更轻） */
.tip-soft{display:flex;align-items:center;gap:7px;font-size:12px;color:var(--sub);background:transparent;border:none;border-radius:8px;padding:0 2px 4px;margin-bottom:8px;opacity:.85}
.tip-soft .em{font-size:14px;opacity:.9}
.overload-tip{display:none;align-items:center;gap:8px;font-size:12.5px;color:var(--warn-txt);background:var(--warn-bg);border:1px solid var(--warn-bd);border-radius:8px;padding:9px 14px;margin-bottom:14px}
.overload-tip.show{display:flex}
.overload-tip .em{font-size:15px}
.overload-tip b{font-weight:700;color:var(--warn-txt)}

/* 翻页器 */
.pager{display:flex;justify-content:flex-end;align-items:center;gap:12px;margin-top:14px;font-size:12.5px;color:var(--sub)}
.pager button{border:1px solid var(--btn-border);background:#fff;color:var(--sub);border-radius:7px;padding:7px 14px;font-size:12.5px;cursor:pointer;transition:all .15s;min-width:66px}
.pager button:hover:not(:disabled){border-color:#C9BBA8;color:var(--txt)}
.pager button:disabled{opacity:.4;cursor:not-allowed}
.pager .pg-info{font-variant-numeric:tabular-nums}

/* 最后一条俏皮提示（表格内） */
.end-tip td{border-bottom:none;background:transparent;padding:10px 0}
.end-tip .msg{display:flex;align-items:center;gap:8px;justify-content:center;font-size:12px;color:var(--sub);background:transparent;border:none;opacity:.85;padding:6px 0}
.end-tip .em{font-size:15px}
.m-end-tip{display:none}
@media(max-width:640px){
  .m-end-tip{display:block;margin-top:12px}
  .m-end-tip .msg{display:flex;align-items:center;gap:8px;justify-content:center;font-size:12px;color:var(--sub);background:transparent;border:none;opacity:.85;padding:6px 0}
  .m-end-tip .em{font-size:15px}
}

/* 二次确认弹窗 */
.confirm{position:fixed;inset:0;z-index:60;display:none;align-items:center;justify-content:center;background:rgba(58,56,53,.32)}
.confirm.open{display:flex}
.confirm-box{background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:26px 28px;max-width:340px;width:88vw;box-shadow:0 12px 40px rgba(58,56,53,.16);text-align:center}
.confirm-box .ico{font-size:30px;margin-bottom:10px}
.confirm-box .msg{font-size:15px;color:var(--txt);font-weight:600;line-height:1.5;margin-bottom:22px}
.confirm-box .btns{display:flex;gap:12px;justify-content:center}
.confirm-box button{flex:1;padding:11px 0;border-radius:8px;font-size:13.5px;cursor:pointer;border:1px solid transparent;font-weight:600;transition:all .15s}
.confirm-yes{background:#E2EFDE;color:#2F472A;border-color:#C9DCC2}
.confirm-yes:hover{filter:brightness(.96)}
.confirm-no{background:#fff;color:var(--sub);border-color:var(--btn-border)}
.confirm-no:hover{border-color:#C9BBA8;color:var(--txt)}

/* Toast */
.toast{position:fixed;left:50%;bottom:36px;transform:translateX(-50%) translateY(20px);background:#3A3835;color:#fff;padding:12px 22px;border-radius:10px;font-size:13px;z-index:70;opacity:0;transition:opacity .25s,transform .25s;pointer-events:none;max-width:80vw;text-align:center}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}

/* 移动端卡片列表 */
.mobile-list{display:none}
.m-card{background:var(--row-bg);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:12px;cursor:pointer;transition:background .12s}
.m-card:hover{background:var(--row-hover)}
.m-card:active{background:#F3EEE6}
.m-card .top{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:8px}
.m-card .key{color:var(--wait-txt);font-weight:600;font-size:14px;text-decoration:none;border-bottom:1.5px dashed transparent}
.m-card .key:hover{border-bottom-color:var(--wait-txt)}
.m-card .name{color:#A8A29C;font-size:12.5px;line-height:1.45;margin-bottom:10px;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.m-card .prog-wrap{margin-bottom:10px}
.m-card .meta{display:flex;flex-wrap:wrap;gap:8px 14px;font-size:11.5px;color:var(--sub)}
.m-card .meta span{background:var(--filter-bg);border:1px solid var(--line);border-radius:6px;padding:4px 8px;white-space:nowrap}
.m-card .meta .lb{color:var(--sub);margin-right:2px}

/* 移动端适配 */
@media(max-width:640px){
  body{padding:14px;line-height:1.45}
  .wrap{max-width:100%;min-width:0}
  .head{padding:16px;gap:10px;flex-direction:column;align-items:center;text-align:center}
  .head .title-wrap{min-width:auto;width:100%}
  .head h1{font-size:20px;white-space:normal}
  .head .meta{font-size:12px;margin-top:4px}
  .head .badge{width:100%;text-align:center}
  .cards{grid-template-columns:repeat(2,1fr);gap:12px;margin:14px 0}
  .card{padding:16px 10px}
  .card-prod .num{font-size:18px}
  .card-prod .lbl{font-size:10.5px}
  .card .num{font-size:28px}
  .card .lbl{font-size:11px}
  .panel{padding:18px 14px;min-width:0}
  .window-info{font-size:12px;padding:10px 12px}
  .window-info .win-fetch{margin-left:0;width:100%;text-align:right}
  .filters{flex-direction:column;align-items:stretch;gap:12px;padding:12px}
  .filters input{width:100%}
  .chk-group{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;width:100%}
  .chk{padding:8px 5px;justify-content:center;text-align:center;font-size:12px;min-height:40px}
  .chk span{white-space:normal;line-height:1.25}
  .reset-btn{margin-left:0;width:100%;margin-top:4px}
  .filters .hint{margin-left:0;text-align:right}
  .tip{font-size:11.5px;padding:8px 12px}
  .tbl-wrap{display:none}
  .mobile-list{display:block}
  .m-card{min-width:0;word-break:break-word;overflow-wrap:anywhere}
  .m-card .key{white-space:normal;word-break:break-word;overflow-wrap:anywhere}
  .m-card .name{word-break:break-word}
  .m-card .meta{gap:8px 10px}
  .m-card .meta span{white-space:normal;word-break:break-word;overflow-wrap:anywhere}
  .pager{justify-content:space-between}
  .foot{font-size:11px;margin-top:14px}
}
@media(max-width:420px){
  .cards{grid-template-columns:1fr 1fr}
  .chk-group{grid-template-columns:repeat(2,1fr)}
}
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <div class="avatar">📋</div>
    <div class="title-wrap">
      <h1>刘莹 · 人力排期看板</h1>
      <div class="meta">测试二部 · 冲刺 <b id="sprint">–</b> · 数据来源：Selene 人力排期</div>
      <div class="tagline" id="tagline"></div>
    </div>
    <div class="badge" id="gen-time">–</div>
  </div>

  <div class="cards" id="cards">
    <div class="card card-total" data-filter="all" title="当前周期内全部任务">
      <div class="num" id="c-total">–</div><div class="lbl">任务总数</div>
      <div class="ctip">🗓️ 未来 7 天排期全貌</div>
    </div>
    <div class="card card-done" data-filter="关闭" title="已完成：状态为【关闭】的任务">
      <div class="num" id="c-done">–</div><div class="lbl">已完成</div>
      <div class="ctip">✅ 已收工，安心喝口茶</div>
    </div>
    <div class="card card-run" data-filter="测试中" title="进行中：状态为【测试中】的任务">
      <div class="num" id="c-run">–</div><div class="lbl">进行中</div>
      <div class="ctip">🔥 测试中，盯紧验收</div>
    </div>
    <div class="card card-wait" data-filter="开始|开发中|开发完成" title="未开始：状态为【开始、开发中、开发完成】的任务">
      <div class="num" id="c-wait">–</div><div class="lbl">未开始</div>
      <div class="ctip">📋 还有这么多没干完，活太多啦～想插需求？挑张看不顺眼的单换掉它 😏</div>
    </div>
    <div class="card card-prod" data-filter="all" title="按产品累计工作量分布（Top3）">
      <div class="num" id="c-prod">–</div><div class="lbl">产品耗时冠军</div>
      <div class="ctip">
        <div class="prod-bars" id="c-prod-bars"></div>
        <div class="prod-legend" id="c-prod-legend"></div>
      </div>
    </div>
  </div>

  <div class="panel">
    <h2>任务明细</h2>
    <div class="tip tip-soft"><span class="em">🍵</span><span>排期已奉上，测试同学正在疯狂输出，进度条是活的，别戳啦~</span></div>
    <div class="window-info" id="win-info"></div>
    <div class="overload-tip" id="overload-tip"><span class="em">⛰️</span><span>全部任务工作量已达 <b id="total-workload">0</b>h，已超负荷运作~ 要注意劳逸结合哦</span></div>
    <div class="filters">
      <input id="q" type="text" placeholder="搜索 任务号 / 任务名称 / 产品 / 客户项目…">
      <div class="chk-group" id="fstatus">
        <label class="chk s-test"><input type="checkbox" value="测试中" checked><span>测试中</span></label>
        <label class="chk s-dev"><input type="checkbox" value="开发完成" checked><span>开发完成</span></label>
        <label class="chk s-start"><input type="checkbox" value="开始"><span>开始</span></label>
        <label class="chk s-dev2"><input type="checkbox" value="开发中"><span>开发中</span></label>
        <label class="chk s-done"><input type="checkbox" value="关闭"><span>关闭</span></label>
      </div>
      <button class="reset-btn" id="reset-btn" type="button">↺ 重置</button>
      <span class="hint" id="count-hint"></span>
    </div>
    <div class="tbl-wrap">
      <table>
        <colgroup>
          <col style="width:190px"><col style="width:88px"><col style="width:96px">
          <col style="width:60px"><col style="width:74px"><col style="width:130px">
          <col style="width:170px"><col style="width:72px">
        </colgroup>
        <thead><tr>
          <th>任务</th><th>Jira 状态</th><th>进度</th>
          <th>工作量</th><th>开始</th><th>产品</th><th>客户项目</th><th>开发人</th>
        </tr></thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
    <div class="mobile-list" id="mobile-list"></div>
    <div class="pager" id="pager"></div>
  </div>

  <div class="foot">由 Selene 人力排期数据生成 · 看板按打开当天动态显示未来 7 天排期 · 可分享给任何人查看 · 点击任务号直达 <span>Jira</span></div>
</div>

<div class="drawer" id="drawer">
  <div class="drawer-mask" id="drawer-mask"></div>
  <div class="drawer-panel">
    <div class="drawer-head">
      <span class="drawer-title">任务详情</span>
      <button class="drawer-close" id="drawer-close" aria-label="关闭">×</button>
    </div>
    <div class="drawer-body" id="drawer-body"></div>
  </div>
</div>

<div class="confirm" id="confirm">
  <div class="confirm-box">
    <div class="ico">🔐</div>
    <div class="msg">你是海鼎员工？</div>
    <div class="btns">
      <button class="confirm-no" id="confirm-no">否</button>
      <button class="confirm-yes" id="confirm-yes">是</button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>

<script>
try {
const D = __DATA__;

const TAGLINES=[
  "☕ 排期已就绪，今天也要元气满满～",
  "🧭 未来 7 天排期一目了然，效率拉满",
  "📌 任务虽多，咱们逐个击破就好",
  "🌱 测试同学的输出，是产品质量的土壤",
  "⛰️ 小山一样的任务，咱们一座座搬",
  "✨ 看板已更新，进度条是活的",
  "🍵 茶已泡好，排期奉上，请慢用",
  "🚀 进度条往前走，bug 往后退",
];
document.getElementById('tagline').textContent=TAGLINES[new Date().getMinutes()%TAGLINES.length];

function today0(){const t=new Date();t.setHours(0,0,0,0);return t;}
function addDays(d,n){const r=new Date(d);r.setDate(d.getDate()+n);return r;}
function fmt(d){return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');}
function parseISO(s){if(!s)return null;const m=s.match(/^(\d{4})-(\d{2})-(\d{2})/);if(!m)return null;return new Date(+m[1],+m[2]-1,+m[3]);}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
function fmtH(h){h=+h;return Number.isInteger(h)?String(h):String(h);}

const TODAY=today0();
const WIN_END=addDays(TODAY,7);
const winTasks=D.tasks.filter(t=>{
  const k=parseISO(t.kickoff)||TODAY;
  const e=parseISO(t.due)||TODAY;
  return e>=TODAY && k<=WIN_END;
});

function updateCards(){
  const total=winTasks.length;
  const doneN=winTasks.filter(t=>t.status==='关闭').length;
  const runN=winTasks.filter(t=>t.status==='测试中').length;
  const waitN=winTasks.filter(t=>t.status==='开发完成'||t.status==='开发中'||t.status==='开始').length;
  document.getElementById('c-total').textContent=total;
  document.getElementById('c-done').textContent=doneN;
  document.getElementById('c-run').textContent=runN;
  document.getElementById('c-wait').textContent=waitN;

  const prodColors=['#C98A5E','#7FB2DA','#8AA877','#BBA37C','#A8A29C'];
  if(D.productDist && D.productDist.length){
    const top=D.productDist[0];
    document.getElementById('c-prod').innerHTML='<span style="font-size:26px">'+esc(top.short)+'</span><span style="font-size:13px"> '+fmtH(top.hours)+'h</span>';
    document.getElementById('c-prod-bars').innerHTML=D.productDist.slice(0,4).map((p,i)=>
      '<div class="prod-seg" style="width:'+p.pct+'%;background:'+prodColors[i%prodColors.length]+'"></div>'
    ).join('');
    document.getElementById('c-prod-legend').innerHTML=D.productDist.slice(0,4).map((p,i)=>
      '<span><i style="background:'+prodColors[i%prodColors.length]+'"></i>'+esc(p.short)+' '+fmtH(p.hours)+'h</span>'
    ).join('');
  }

  if(D.overload){
    document.getElementById('total-workload').textContent=fmtH(D.totalWorkload);
    document.getElementById('overload-tip').classList.add('show');
  }
}

document.getElementById('sprint').textContent=D.sprint;
document.getElementById('gen-time').textContent='生成于 '+D.sprintBegin+' ~ '+D.sprintEnd;

function renderWinInfo(){
  const fetchHtml='最近获取：<b>'+esc(D.lastFetch)+'</b>';
  document.getElementById('win-info').innerHTML=
    '<span class="win-main">当前查看窗口：<b>'+fmt(TODAY)+' ~ '+fmt(WIN_END)+'</b>（今天起未来 7 天）'+
    (winTasks.length===0?' · <span style="color:#a8643a">该窗口内无排期任务，可能冲刺已结束，请联系刘莹重新生成</span>':'')+'</span>'+
    '<span class="win-fetch">'+fetchHtml+'</span>';
}
renderWinInfo();
updateCards();

function badgeClass(s){return s==='开发中'?'tag-dev':(s==='开发完成'?'tag-wait':(s==='关闭'?'tag-done':(s==='开始'?'tag-start':'tag-run')));}
const STATUS_TAG={
  '测试中':'<span class="tag tag-run">测试中</span>',
  '开发中':'<span class="tag tag-dev">开发中</span>',
  '开始':'<span class="tag tag-start">开始</span>',
  '开发完成':'<span class="tag tag-wait">开发完成</span>',
  '关闭':'<span class="tag tag-done">关闭</span>',
};
function progClass(s){
  if(s==='测试中') return ['p-test','pf-test'];
  if(s==='开始') return ['p-start','pf-start'];
  if(s==='开发中') return ['p-dev','pf-dev'];
  if(s==='开发完成') return ['p-done2','pf-done2'];
  if(s==='关闭') return ['p-close','pf-close'];
  return ['p-start','pf-start'];
}
function jiraUrl(key){return 'http://jira6.app.hd123.cn/jira/browse/'+encodeURIComponent(key);}

function getFiltered(){
  const q=document.getElementById('q').value.trim().toLowerCase();
  const checked=[...document.querySelectorAll('#fstatus input:checked')].map(c=>c.value);
  let rows=winTasks.filter(t=>{
    if(checked.length>0 && !checked.includes(t.status)) return false;
    if(q){
      const hay=(t.key+' '+t.summary+' '+t.product+' '+t.proj).toLowerCase();
      if(!hay.includes(q)) return false;
    }
    return true;
  });
  rows.sort((a,b)=>(a.kickoff||'').localeCompare(b.kickoff||'')||(a.due||'').localeCompare(b.due||''));
  return rows;
}
let currentPage=1;
const PAGE_SIZE=10;
function emptyHtml(msg){
  return '<tr><td colspan="8"><div class="empty"><span class="em">🔍</span>'+esc(msg)+'<br>请调整搜索关键词或筛选条件后重试</div></td></tr>';
}
function renderTbody(rows, pageRows, isLastPage){
  const tb=document.getElementById('tbody');
  if(rows.length===0){
    tb.innerHTML=emptyHtml('未找到匹配的任务');
    return;
  }
  let html=pageRows.map(t=>{
    const [pb,pf]=progClass(t.status);
    const pct=t.progress;
    const progHtml='<div class="prog" title="进度 '+pct+'%（'+esc(t.status)+'）">'+
      '<span class="prog-pct">'+pct+'%</span>'+
      '<div class="prog-bar '+pb+'"><div class="prog-fill '+pf+'" style="width:'+pct+'%"></div></div>'+
      '</div>';
    return '<tr data-key="'+esc(t.key)+'">'+
      '<td class="task-cell">'+
        '<a class="task-key" onclick="confirmJira('+JSON.stringify(t.key)+')">'+esc(t.key)+'</a>'+
        '<div class="task-name" title="'+esc(t.summary)+'">'+esc(t.summary)+'</div>'+
      '</td>'+
      '<td>'+(STATUS_TAG[t.status]||esc(t.status))+'</td>'+
      '<td>'+progHtml+'</td>'+
      '<td class="mono nowrap">'+t.workload+'</td>'+
      '<td class="nowrap">'+esc(t.kickoff.slice(5))+'</td>'+
      '<td title="'+esc(t.product)+'"><span class="cell">'+esc(t.product)+'</span></td>'+
      '<td title="'+esc(t.proj)+'"><span class="cell">'+esc(t.proj)+'</span></td>'+
      '<td class="nowrap">'+esc(t.starter||'')+'</td>'+
      '</tr>';
  }).join('');
  if(isLastPage && pageRows.length>0){
    html+='<tr class="end-tip"><td colspan="8"><div class="msg"><span class="em">⛰️</span>任务单还在持续叠加中，工作量已经像小山一样高了~</div></td></tr>';
  }
  tb.innerHTML=html;
}
function renderMobile(rows, pageRows, isLastPage){
  const el=document.getElementById('mobile-list');
  if(rows.length===0){
    el.innerHTML='<div class="empty"><span class="em">🔍</span>未找到匹配的任务<br>请调整搜索关键词或筛选条件后重试</div>';
    return;
  }
  let html=pageRows.map(t=>{
    const [pb,pf]=progClass(t.status);
    return '<div class="m-card" data-key="'+esc(t.key)+'">'+
      '<div class="top">'+
        '<a class="key" onclick="confirmJira('+JSON.stringify(t.key)+')">'+esc(t.key)+'</a>'+
        (STATUS_TAG[t.status]||esc(t.status))+
      '</div>'+
      '<div class="name">'+esc(t.summary)+'</div>'+
      '<div class="prog-wrap">'+
        '<div class="prog" title="进度 '+t.progress+'%">'+
          '<span class="prog-pct">'+t.progress+'%</span>'+
          '<div class="prog-bar '+pb+'"><div class="prog-fill '+pf+'" style="width:'+t.progress+'%"></div></div>'+
        '</div>'+
      '</div>'+
      '<div class="meta">'+
        '<span><span class="lb">工作量</span>'+t.workload+'</span>'+
        '<span><span class="lb">开始</span>'+esc(t.kickoff)+'</span>'+
        '<span><span class="lb">产品</span>'+esc(t.product||'—')+'</span>'+
        '<span><span class="lb">客户项目</span>'+esc(t.proj||'—')+'</span>'+
        '<span><span class="lb">开发人</span>'+esc(t.starter||'—')+'</span>'+
      '</div>'+
    '</div>';
  }).join('');
  if(isLastPage && pageRows.length>0){
    html+='<div class="m-end-tip"><div class="msg"><span class="em">⛰️</span>任务单还在持续叠加中，工作量已经像小山一样高了~</div></div>';
  }
  el.innerHTML=html;
}
function renderPager(total){
  const totalPages=Math.max(1,Math.ceil(total/PAGE_SIZE));
  if(currentPage>totalPages)currentPage=totalPages;
  if(currentPage<1)currentPage=1;
  const el=document.getElementById('pager');
  el.innerHTML=
    '<button id="pg-prev" '+(currentPage<=1?'disabled':'')+'>上一页</button>'+
    '<span class="pg-info">第 '+currentPage+' / '+totalPages+' 页</span>'+
    '<button id="pg-next" '+(currentPage>=totalPages?'disabled':'')+'>下一页</button>';
  const prev=document.getElementById('pg-prev');
  const next=document.getElementById('pg-next');
  if(prev)prev.addEventListener('click',()=>{if(currentPage>1){currentPage--;render();}});
  if(next)next.addEventListener('click',()=>{if(currentPage<totalPages){currentPage++;render();}});
}
function render(){
  const rows=getFiltered();
  document.getElementById('count-hint').textContent='显示 '+rows.length+' / '+winTasks.length+' 条';
  renderPager(rows.length);
  const start=(currentPage-1)*PAGE_SIZE;
  const pageRows=rows.slice(start,start+PAGE_SIZE);
  const totalPages=Math.max(1,Math.ceil(rows.length/PAGE_SIZE));
  const isLastPage=currentPage>=totalPages;
  renderTbody(rows, pageRows, isLastPage);
  renderMobile(rows, pageRows, isLastPage);
}

/* 二次确认弹窗 + Toast（点击任务号） */
let pendingKey=null;
const confirmEl=document.getElementById('confirm');
function confirmJira(key){
  pendingKey=key;
  confirmEl.classList.add('open');
}
// 暴露到 window：内联 onclick="confirmJira(...)" 运行在全局作用域，
// 而本函数定义在 try 块内（块级作用域），不暴露会导致点击报「confirmJira is not defined」
window.confirmJira = confirmJira;
document.getElementById('confirm-yes').addEventListener('click',()=>{
  confirmEl.classList.remove('open');
  if(pendingKey)window.open(jiraUrl(pendingKey),'_blank');
  pendingKey=null;
});
document.getElementById('confirm-no').addEventListener('click',()=>{
  confirmEl.classList.remove('open');
  showToast('很抱歉，你没有权限查看任务详情');
  pendingKey=null;
});
confirmEl.addEventListener('click',e=>{if(e.target===confirmEl){confirmEl.classList.remove('open');pendingKey=null;}});
let toastTimer=null;
function showToast(msg){
  const el=document.getElementById('toast');
  el.textContent=msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>el.classList.remove('show'),2600);
}

document.getElementById('q').addEventListener('input',()=>{currentPage=1;render();});
document.querySelectorAll('#fstatus input').forEach(c=>c.addEventListener('change',()=>{currentPage=1;syncCardActive();render();}));

// 重置按钮
document.getElementById('reset-btn').addEventListener('click',()=>{
  document.querySelectorAll('#fstatus input').forEach(b=>{b.checked=(b.value==='测试中'||b.value==='开发完成');});
  document.getElementById('q').value='';
  currentPage=1;syncCardActive();render();
});

// 卡片点击筛选
const cardsEl=document.getElementById('cards');
cardsEl.addEventListener('click',e=>{
  const card=e.target.closest('.card');
  if(!card) return;
  const f=card.dataset.filter;
  const boxes=[...document.querySelectorAll('#fstatus input')];
  if(f==='all'){boxes.forEach(b=>b.checked=true);}
  else{const set=f.split('|');boxes.forEach(b=>b.checked=set.includes(b.value));}
  if(f==='开始|开发中|开发完成'){
    showToast('📋 还有这么多没干完的活，想插需求？把你看不顺眼的那张任务单换掉它 😏');
  }
  currentPage=1;syncCardActive();render();
});
function syncCardActive(){
  const boxes=[...document.querySelectorAll('#fstatus input')];
  const checked=boxes.filter(b=>b.checked).map(b=>b.value);
  const allSet=new Set(['测试中','开发完成','开始','开发中','关闭']);
  const checkedSet=new Set(checked);
  const isAll=checked.length===boxes.length;
  const match=(f)=>{if(f==='all')return isAll;return f.split('|').every(s=>checkedSet.has(s))&&f.split('|').length===checked.length;};
  document.querySelectorAll('#cards .card').forEach(c=>{c.classList.toggle('active',match(c.dataset.filter));});
}

// 行点击 / 卡片点击 → 侧边详情弹窗
const drawer=document.getElementById('drawer');
function openDrawer(t){
  const [pb,pf]=progClass(t.status);
  const rows=[
    ['任务号','<a class="task-key" onclick="confirmJira('+JSON.stringify(t.key)+')">'+esc(t.key)+'</a>'],
    ['任务名称',esc(t.summary)],
    ['Jira 状态',(STATUS_TAG[t.status]||esc(t.status))],
    ['进度','<div class="prog" style="margin-top:2px"><span class="prog-pct">'+t.progress+'%</span><div class="prog-bar '+pb+'"><div class="prog-fill '+pf+'" style="width:'+t.progress+'%"></div></div></div>'],
    ['工作量',String(t.workload)],
    ['开始日期',esc(t.kickoff)],
    ['截止日期',esc(t.due)],
    ['产品',esc(t.product)],
    ['客户项目',esc(t.proj)],
    ['开发人',esc(t.starter||'—')],
  ];
  document.getElementById('drawer-body').innerHTML=
    '<div class="dl">'+rows.map(r=>'<div class="row"><div class="k">'+r[0]+'</div><div class="v">'+r[1]+'</div></div>').join('<hr>')+'</div>';
  drawer.classList.add('open');
}
document.getElementById('tbody').addEventListener('click',e=>{
  const tr=e.target.closest('tr[data-key]');
  if(!tr) return;
  if(e.target.closest('a')) return;
  const key=tr.dataset.key;
  const t=D.tasks.find(x=>x.key===key)||winTasks.find(x=>x.key===key);
  if(t) openDrawer(t);
});
document.getElementById('mobile-list').addEventListener('click',e=>{
  const card=e.target.closest('.m-card');
  if(!card) return;
  if(e.target.closest('a')) return;
  const key=card.dataset.key;
  const t=D.tasks.find(x=>x.key===key)||winTasks.find(x=>x.key===key);
  if(t) openDrawer(t);
});
document.getElementById('drawer-close').addEventListener('click',()=>drawer.classList.remove('open'));
document.getElementById('drawer-mask').addEventListener('click',()=>drawer.classList.remove('open'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')drawer.classList.remove('open');});

syncCardActive();
render();

} catch (err) {
  console.error(err);
  document.body.innerHTML='<div style="max-width:480px;margin:80px auto;padding:36px;background:#fff;border:1px solid #E4E0DA;border-radius:12px;text-align:center;color:#7A756F;font-family:sans-serif;line-height:1.9">'+
    '<div style="font-size:42px;margin-bottom:14px">☕</div>'+
    '<h2 style="color:#3A3835;margin-bottom:12px;font-size:18px">看板未成功加载，请稍后再看~</h2>'+
    '<p style="font-size:13px">可能是数据正在刷新或网络波动，稍后刷新一下就好。</p>'+
    '</div>';
}
</script>
</body>
</html>
"""

html = HTML.replace('__DATA__', data_json)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)
print("written:", OUT, os.path.getsize(OUT), "bytes")
print("tasks (no MASK01, no TM):", len(simplified))
