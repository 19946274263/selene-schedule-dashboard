// CloudBase HTTP 云函数：代理 Selene 实时拉取刘莹人力排期
// 浏览器直连 Selene 会受跨域 / 明文 token / 混合内容限制，故由服务端代理。
// token 通过环境变量 SELENE_TOKEN 注入（不写死在代码，过期后只需更新环境变量）。
const API = 'http://selene.hd123.cn:52163/selene/v1/plan/gantt/employee/query';

// 返回 Date 对象，其 UTC 字段即北京时间数值（时区无关：本地绝对时间 +8h 换算成北京时间，再对日期加减 offsetDays）
function bjDate(offsetDays) {
  const d = new Date(Date.now() + 8 * 3600 * 1000); // 当前北京时间（用 UTC 字段承载 BJ 数值）
  d.setUTCDate(d.getUTCDate() + offsetDays); // 在「北京时间」框架下加减天数，避免时区偏移与天数偏移混淆
  return d;
}
function fmtDate(dt) {
  const y = dt.getUTCFullYear();
  const m = String(dt.getUTCMonth() + 1).padStart(2, '0');
  const d = String(dt.getUTCDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}
function fmtBJ(dt) {
  return fmtDate(dt) + ' ' + String(dt.getUTCHours()).padStart(2, '0') + ':' + String(dt.getUTCMinutes()).padStart(2, '0');
}
function decodeExp(token) {
  try {
    const p = token.split('.')[1];
    const pad = p + '='.repeat((4 - (p.length % 4)) % 4);
    const payload = JSON.parse(Buffer.from(pad, 'base64').toString('utf8'));
    if (payload.exp) return new Date(payload.exp * 1000 + 8 * 3600 * 1000); // 北京时间 Date
  } catch (e) {}
  return null;
}
function toIso(s) { return s ? String(s).slice(0, 10) : null; }
function shortName(p) {
  const parts = String(p).split('-');
  const ascii = parts.filter(x => x && !/[一-龥]/.test(x));
  return ascii.length ? ascii[ascii.length - 1] : String(p).slice(0, 4);
}

// 复刻 gen_dashboard_v2.py 的简化转换，保证与 __DATA__ 同构，前端 applyData 直接可用
function transform(json) {
  const data = json.data || {};
  const emp = (data.employees && data.employees[0]) || {};
  const tasksRaw = emp.tasks || [];
  const simplified = [];
  for (const t of tasksRaw) {
    const key = t.key || '';
    if (key.startsWith('MASK01') || key.startsWith('TM-')) continue;
    const prev = t.prev || {};
    simplified.push({
      key,
      summary: t.summary || '',
      status: t.status || '',
      progress: Math.round((t.progress || 0) * 100),
      workload: t.workload || 0,
      kickoff: toIso(t.ganttKickoffDate || t.kickoffDate) || '',
      due: toIso(t.ganttDueDate || t.dueDate) || '',
      done: !!t.done,
      product: t.product || '',
      proj: t.customerProject || '',
      starterName: t.starterName || '',
      starter: t.starter || '',
      prev: { employeeName: prev.employeeName || '', employee: prev.employee || '' },
    });
  }
  simplified.sort((a, b) =>
    (a.kickoff || '9999').localeCompare(b.kickoff || '9999') ||
    (a.due || '9999').localeCompare(b.due || '9999') ||
    a.key.localeCompare(b.key));

  const totalWorkload = Math.round(simplified.reduce((s, t) => s + (t.workload || 0), 0) * 10) / 10;
  const overload = totalWorkload > 40;
  const prodWl = {};
  for (const t of simplified) {
    const pr = (t.product || '').trim() || '未分类';
    prodWl[pr] = (prodWl[pr] || 0) + (t.workload || 0);
  }
  const prodDist = Object.keys(prodWl).map(p => ({ product: p, hours: Math.round(prodWl[p] * 10) / 10, short: shortName(p) }));
  prodDist.sort((a, b) => b.hours - a.hours);
  for (const it of prodDist) it.pct = totalWorkload ? Math.round(it.hours / totalWorkload * 1000) / 10 : 0;
  const productChamp = prodDist.length ? { short: prodDist[0].short.toUpperCase(), hours: prodDist[0].hours } : { short: '—', hours: 0 };

  const begin = fmtDate(bjDate(-2));
  const end = fmtDate(bjDate(4));
  const sprint = begin.slice(5).replace(/-/g, '') + '~' + end.slice(5).replace(/-/g, '');
  return {
    empName: emp.employeeName || '',
    empId: emp.employee || '',
    dept: emp.department || '',
    sprint, sprintBegin: begin, sprintEnd: end,
    totalWorkload, overload, productDist: prodDist, productChamp, tasks: simplified,
  };
}

function corsHeaders() {
  return {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
  };
}
function resp(statusCode, bodyObj, extraHeaders) {
  return { statusCode, headers: Object.assign(corsHeaders(), extraHeaders || {}), body: JSON.stringify(bodyObj) };
}
function expiredPayload(expDt, nowBJ) {
  return {
    tokenExpired: true,
    tokenExp: expDt ? fmtBJ(expDt) : '',
    lastFetch: fmtBJ(nowBJ),
    tasks: [], totalWorkload: 0, overload: false,
    productDist: [], productChamp: { short: '—', hours: 0 }, empName: '',
  };
}

exports.main = async (event, context) => {
  if ((event.httpMethod || '').toUpperCase() === 'OPTIONS') {
    return { statusCode: 204, headers: corsHeaders(), body: '' };
  }
  const token = process.env.SELENE_TOKEN || '';
  const nowBJ = bjDate(0);
  if (!token) {
    return resp(500, { error: '云端 SELENE_TOKEN 未配置，请联系管理员更新', tokenExpired: false });
  }
  const expDt = decodeExp(token);
  if (expDt && expDt < nowBJ) {
    return resp(200, expiredPayload(expDt, nowBJ));
  }
  // 拉取范围扩大到前后各 3 周，前端按所选周期子窗口过滤
  const begin = fmtDate(bjDate(-21));
  const end = fmtDate(bjDate(21));
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 25000);
    const r = await fetch(API, {
      method: 'POST',
      headers: {
        'Authorization': token,
        'x-requested-with': 'XMLHttpRequest',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        beginDate: begin, endDate: end,
        departments: ['测试二部'], employees: ['liuying'], queryRef: false,
      }),
      signal: ctrl.signal,
    });
    clearTimeout(timer);
    if (r.status === 401 || r.status === 403) {
      return resp(200, expiredPayload(expDt, nowBJ));
    }
    const json = await r.json();
    const payload = transform(json);
    payload.lastFetch = fmtBJ(nowBJ);
    payload.tokenExp = expDt ? fmtBJ(expDt) : '';
    payload.tokenExpired = false;
    return resp(200, payload);
  } catch (e) {
    return resp(502, { error: 'Selene 请求失败: ' + (e && e.message ? e.message : String(e)), tokenExpired: false });
  }
};
