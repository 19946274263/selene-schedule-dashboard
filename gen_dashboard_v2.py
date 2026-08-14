# -*- coding: utf-8 -*-
"""生成刘莹人力排期看板 HTML — 抹茶绿马卡龙配色 + 精简统计 + 新列口径"""
import json, os
from collections import Counter

TEMP = os.environ.get('TEMP', '')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '刘莹_人力排期看板.html')

# 数据源：优先读取同目录下的快照，找不到再回退系统 TEMP
_src = os.path.join(HERE, 'gantt_0814_0821.json')
if not os.path.exists(_src):
    _src = os.path.join(TEMP, 'gantt_0814_0821.json')
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

print("过滤后状态分布:", dict(Counter(t['status'] for t in simplified)))

payload = {
    'empName': emp.get('employeeName', ''),
    'empId': emp.get('employee', ''),
    'dept': emp.get('department', ''),
    'sprint': '0814~0821',
    'sprintBegin': data.get('beginDate', '')[:10],
    'sprintEnd': data.get('endDate', '')[:10],
    'tasks': simplified,
}
data_json = json.dumps(payload, ensure_ascii=False)

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>刘莹 · 人力排期看板</title>
<style>
:root{
  --bg:#f5f8ef;--card:#fff;--line:#d9e7c8;
  --txt:#3a4a2c;--sub:#7a8a64;--brand:#5a8a3c;
  --head:#eaf2dd;--head-2:#c2dc9f;--head-deep:#3e6b2e;--head-mid:#6b9a4e;
  --c1:#eaf2dd;--c2:#cfe3b0;--c3:#b3d488;--c4:#9cc66e;
  --sky-l:#e0f2fe;--sky-d:#0369a1;
  --teal-l:#ccfbf1;--teal-d:#0f766e;
  --violet-l:#ede9fe;--violet-d:#6d28d9;
  --amber-l:#fef3c7;--amber-d:#92400e;
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;padding:24px;line-height:1.5}
.wrap{max-width:1180px;margin:0 auto}
.head{background:var(--head);border:1px solid #c8e0a8;border-radius:18px;padding:24px 30px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.head .avatar{width:46px;height:46px;border-radius:50%;background:var(--head-2);color:var(--head-deep);display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:600;flex-shrink:0}
.head .title-wrap{flex:1;min-width:0}
.head h1{font-size:22px;font-weight:700;color:var(--head-deep);letter-spacing:.3px}
.head .meta{font-size:13px;color:var(--head-mid);margin-top:6px}
.head .badge{background:#fff;border:1px solid #a7cc86;border-radius:999px;padding:9px 15px;font-size:13px;color:var(--head-deep);font-weight:500;flex-shrink:0}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:20px 0}
@media(max-width:780px){.cards{grid-template-columns:repeat(2,1fr)}}
.card{border-radius:14px;padding:20px 22px;text-align:center;border:1px solid rgba(62,107,46,.08)}
.card-total{background:var(--c1)}
.card-done{background:var(--c2)}
.card-run{background:var(--c3)}
.card-wait{background:var(--c4)}
.card .num{font-size:34px;font-weight:800;line-height:1.1;color:var(--head-deep)}
.card-wait .num{color:#2c5220}
.card .lbl{font-size:12px;margin-top:8px;font-weight:500;color:var(--head-mid);line-height:1.35}
.panel{background:var(--card);border-radius:16px;padding:24px 28px;border:1px solid var(--line);box-shadow:0 2px 10px rgba(90,138,60,.05)}
.panel h2{font-size:17px;font-weight:700;margin-bottom:16px;display:flex;align-items:center;gap:8px;color:var(--txt)}
.panel h2::before{content:"";width:5px;height:18px;background:var(--brand);border-radius:3px}
.window-info{font-size:13px;color:var(--sub);margin-bottom:16px;background:#f0f5e6;border-radius:10px;padding:12px 16px;border:1px solid var(--line)}
.window-info b{color:var(--brand)}
.filters{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;align-items:center}
.filters input{padding:9px 14px;border:1px solid var(--line);border-radius:10px;font-size:13px;background:#fff;color:var(--txt);outline:none;transition:border-color .2s,box-shadow .2s}
.filters input:focus{border-color:var(--brand);box-shadow:0 0 0 3px rgba(90,138,60,.12)}
.filters input{width:280px}
.filters .hint{font-size:12px;color:var(--sub);margin-left:auto}
.chk-group{display:flex;gap:6px;flex-wrap:wrap}
.chk{display:inline-flex;align-items:center;gap:4px;padding:7px 12px;border:1px solid var(--line);border-radius:10px;font-size:13px;cursor:pointer;user-select:none;transition:all .2s;background:#fff}
.chk:hover{border-color:var(--brand)}
.chk input{width:auto;margin:0;cursor:pointer;accent-color:var(--brand)}
.chk:has(input:checked){background:var(--c1);border-color:#9cc66e;color:var(--head-deep);font-weight:600}
.tbl-wrap{overflow:auto;max-height:600px;border:1px solid var(--line);border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:12.5px;min-width:980px}
thead th{position:sticky;top:0;background:var(--c1);z-index:2;text-align:left;padding:11px 12px;font-weight:600;color:var(--head-deep);border-bottom:2px solid #c8e0a8;white-space:nowrap}
tbody td{padding:10px 12px;border-bottom:1px solid #eff5e6;vertical-align:top}
tbody tr:hover{background:#f1f7e8}
.cell{max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nowrap{white-space:nowrap}
.key a{color:var(--head-deep);font-weight:600;white-space:nowrap;text-decoration:none;border-bottom:1.5px dashed transparent;transition:all .2s}
.key a:hover{color:var(--brand);border-bottom-color:var(--brand)}
.tag{display:inline-block;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:600;white-space:nowrap}
.tag-run{background:var(--sky-l);color:var(--sky-d)}
.tag-dev{background:var(--violet-l);color:var(--violet-d)}
.tag-wait{background:var(--amber-l);color:var(--amber-d)}
.tag-done{background:var(--teal-l);color:var(--teal-d)}
.mono{font-variant-numeric:tabular-nums}
.empty{text-align:center;padding:40px 20px;color:var(--sub);font-size:14px}
.foot{margin-top:18px;text-align:center;color:var(--sub);font-size:12px}
.foot span{color:var(--brand);font-weight:500}
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <div class="avatar">刘</div>
    <div class="title-wrap">
      <h1>刘莹 · 人力排期看板</h1>
      <div class="meta">测试二部 · 冲刺 <b id="sprint">–</b> · 数据来源：Selene 人力排期</div>
    </div>
    <div class="badge" id="gen-time">–</div>
  </div>

  <div class="cards">
    <div class="card card-total"><div class="num" id="c-total">–</div><div class="lbl">任务总数</div></div>
    <div class="card card-done"><div class="num" id="c-done">–</div><div class="lbl">已完成</div></div>
    <div class="card card-run"><div class="num" id="c-run">–</div><div class="lbl">进行中</div></div>
    <div class="card card-wait"><div class="num" id="c-wait">–</div><div class="lbl">未开始</div></div>
  </div>

  <div class="panel">
    <h2>任务明细</h2>
    <div class="window-info" id="win-info"></div>
    <div class="filters">
      <input id="q" type="text" placeholder="搜索 任务号 / 摘要 / 产品 / 客户项目…">
      <div class="chk-group" id="fstatus">
        <label class="chk"><input type="checkbox" value="测试中" checked><span>测试中</span></label>
        <label class="chk"><input type="checkbox" value="开发完成" checked><span>开发完成</span></label>
        <label class="chk"><input type="checkbox" value="开始"><span>开始</span></label>
        <label class="chk"><input type="checkbox" value="开发中"><span>开发中</span></label>
        <label class="chk"><input type="checkbox" value="关闭"><span>关闭</span></label>
      </div>
      <span class="hint" id="count-hint"></span>
    </div>
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th>任务号</th><th>摘要</th><th>Jira 状态</th><th>进度</th>
          <th>工作量</th><th>开始</th><th>产品</th><th>客户项目</th><th>提单人</th>
        </tr></thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
  </div>

  <div class="foot">由 Selene 人力排期数据生成 · 看板按打开当天动态显示未来 7 天排期 · 可分享给任何人查看 · 点击任务号直达 <span>Jira</span></div>
</div>

<script>
const D = __DATA__;

function today0(){const t=new Date();t.setHours(0,0,0,0);return t;}
function addDays(d,n){const r=new Date(d);r.setDate(d.getDate()+n);return r;}
function fmt(d){return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');}
function parseISO(s){if(!s)return null;const m=s.match(/^(\d{4})-(\d{2})-(\d{2})/);if(!m)return null;return new Date(+m[1],+m[2]-1,+m[3]);}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}

const TODAY=today0();
const WIN_END=addDays(TODAY,7);
const winTasks=D.tasks.filter(t=>{
  const k=parseISO(t.kickoff)||TODAY;
  const e=parseISO(t.due)||TODAY;
  return e>=TODAY && k<=WIN_END;
});

// 统计卡（固定基于窗口内全部任务，不随筛选变化）
function updateCards(){
  const total=winTasks.length;
  const doneN=winTasks.filter(t=>t.status==='关闭').length;
  const runN=winTasks.filter(t=>t.status==='测试中').length;
  const waitN=winTasks.filter(t=>t.status==='开发完成'||t.status==='开发中'||t.status==='开始').length;
  document.getElementById('c-total').textContent=total;
  document.getElementById('c-done').textContent=doneN;
  document.getElementById('c-run').textContent=runN;
  document.getElementById('c-wait').textContent=waitN;
}

document.getElementById('sprint').textContent=D.sprint;
document.getElementById('gen-time').textContent='生成于 '+D.sprintBegin+' ~ '+D.sprintEnd;
document.getElementById('win-info').innerHTML=
  '当前查看窗口：<b>'+fmt(TODAY)+' ~ '+fmt(WIN_END)+'</b>（今天起未来 7 天）'+
  (winTasks.length===0?' · <span style="color:#e25555">该窗口内无排期任务，可能冲刺已结束，请联系刘莹重新生成</span>':'');

updateCards();

const STATUS_TAG={
  '测试中':'<span class="tag tag-run">测试中</span>',
  '开发中':'<span class="tag tag-dev">开发中</span>',
  '开始':'<span class="tag tag-run">开始</span>',
  '开发完成':'<span class="tag tag-wait">开发完成</span>',
  '关闭':'<span class="tag tag-done">关闭</span>',
};

function render(){
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

  document.getElementById('count-hint').textContent='显示 '+rows.length+' / '+winTasks.length+' 条';
  const tb=document.getElementById('tbody');
  if(rows.length===0){
    tb.innerHTML='<tr><td colspan="9"><div class="empty">无匹配任务</div></td></tr>';
    return;
  }
  tb.innerHTML=rows.map(t=>'<tr>'+
    '<td class="nowrap key"><a href="http://jira6.app.hd123.cn/jira/browse/'+esc(t.key)+'" target="_blank" rel="noopener" onclick="window.open(this.href,\'_blank\');return false;">'+esc(t.key)+'</a></td>'+
    '<td title="'+esc(t.summary)+'"><div class="cell">'+esc(t.summary)+'</div></td>'+
    '<td>'+(STATUS_TAG[t.status]||esc(t.status))+'</td>'+
    '<td class="mono nowrap">'+t.progress+'%</td>'+
    '<td class="mono nowrap">'+t.workload+'</td>'+
    '<td class="nowrap">'+esc(t.kickoff.slice(5))+'</td>'+
    '<td class="nowrap" title="'+esc(t.product)+'">'+esc(t.product)+'</td>'+
    '<td title="'+esc(t.proj)+'"><div class="cell">'+esc(t.proj)+'</div></td>'+
    '<td class="nowrap">'+esc(t.starter||'')+'</td>'+
    '</tr>').join('');
}
document.getElementById('q').addEventListener('input',render);
document.querySelectorAll('#fstatus input').forEach(c=>c.addEventListener('change',render));
render();
</script>
</body>
</html>
"""
html = HTML.replace('__DATA__', data_json)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)
print("written:", OUT, os.path.getsize(OUT), "bytes")
print("tasks (no MASK01, no TM):", len(simplified))
