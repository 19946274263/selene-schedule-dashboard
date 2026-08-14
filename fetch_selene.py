# -*- coding: utf-8 -*-
"""从 Selene 实时拉取人力排期数据，保存快照并重新生成看板。

用法：
  # 方式一：环境变量传入 token
  set SELENE_TOKEN=xxxx
  python fetch_selene.py

  # 方式二：把 token 写入同目录 selene_token.txt（不要提交到公开仓库）
  python fetch_selene.py

  # 每小时自动刷新（Windows 任务计划）：用 schtasks 指向本脚本即可

token 获取：登录 Selene 网页后，从浏览器 DevTools → Application → Local Storage →
  http://selene.hd123.cn:52163  → 找到 vuex 里的 token 字段复制。
注意：Selene token 会过期（通常 24 小时），过期后脚本会标记「token 已过期」并沿用旧数据，
  需重新从浏览器取一次 token 再运行。
"""
import os, sys, json, datetime, base64, urllib.request, urllib.error, subprocess, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
API = "http://selene.hd123.cn:52163/selene/v1/plan/gantt/employee/query"
OUT_JSON = os.path.join(HERE, "gantt_live.json")
STATIC_JSON = os.path.join(HERE, "gantt_0814_0821.json")
DEPLOY_HTML = os.path.join(HERE, "deploy", "index.html")
GEN_HTML = os.path.join(HERE, "刘莹_人力排期看板.html")

BJ = datetime.timezone(datetime.timedelta(hours=8))


def bj_now():
    return datetime.datetime.now(BJ)


def get_token():
    t = os.environ.get("SELENE_TOKEN", "").strip()
    if t:
        return t
    p = os.path.join(HERE, "selene_token.txt")
    if os.path.exists(p):
        return open(p, encoding="utf-8").read().strip()
    return ""


def decode_token_exp(token):
    """解码 JWT 取 exp，返回北京时间 datetime；失败返回 None。"""
    try:
        _, p, _ = token.split(".")
        p += "=" * (-len(p) % 4)
        payload = json.loads(base64.urlsafe_b64decode(p))
        exp = payload.get("exp")
        if exp:
            return datetime.datetime.fromtimestamp(exp, datetime.timezone.utc).astimezone(BJ)
    except Exception:
        pass
    return None


def window_days(n=7):
    today = bj_now().date()
    end = today + datetime.timedelta(days=n)
    f = lambda d: d.strftime("%Y-%m-%d")
    return f(today), f(end)


def copy_to_deploy():
    try:
        os.makedirs(os.path.dirname(DEPLOY_HTML), exist_ok=True)
        shutil.copyfile(GEN_HTML, DEPLOY_HTML)
        print(f"[OK] 已同步到部署目录 {DEPLOY_HTML}")
    except Exception as e:
        print(f"[提示] 部署目录同步跳过：{e}")


def regenerate():
    print("[信息] 重新生成看板…")
    subprocess.run([sys.executable, os.path.join(HERE, "gen_dashboard_v2.py")], check=True)
    copy_to_deploy()


def mark_expired_and_regenerate(exp_dt):
    """token 已过期/无权访问：沿用上一次成功快照，标记过期后重新生成。"""
    src = OUT_JSON if os.path.exists(OUT_JSON) else STATIC_JSON
    try:
        d = json.load(open(src, encoding="utf-8"))
        d["tokenExpired"] = True
        if exp_dt:
            d["tokenExp"] = exp_dt.strftime("%Y-%m-%d %H:%M")
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print(f"[信息] 沿用旧快照 {os.path.basename(src)} 并标记「token 已过期」，重新生成看板。")
        regenerate()
    except Exception as e:
        print(f"[错误] 无法沿用旧快照：{e}")


def fetch():
    token = get_token()
    if not token:
        print("[错误] 未找到 Selene token。请设置环境变量 SELENE_TOKEN 或写入 selene_token.txt")
        sys.exit(1)

    exp_dt = decode_token_exp(token)
    if exp_dt and exp_dt < bj_now():
        print(f"[错误] token 已于 {exp_dt:%Y-%m-%d %H:%M}（北京时间）过期，请到浏览器重新复制新 token。")
        mark_expired_and_regenerate(exp_dt)
        sys.exit(4)
    if exp_dt:
        print(f"[信息] token 有效至 {exp_dt:%Y-%m-%d %H:%M}（北京时间）")
    else:
        print("[警告] 无法解析 token 有效期，仍尝试请求（若返回 401/403 会标记过期）。")

    begin, end = window_days(7)
    payload = {
        "beginDate": begin,
        "endDate": end,
        "departments": ["测试二部"],
        "employees": ["liuying"],
        "queryRef": False,
    }
    req = urllib.request.Request(
        API,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": token,
            "x-requested-with": "XMLHttpRequest",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print(f"[错误] HTTP {e.code}：token 可能已过期或无权访问，请到浏览器重新复制新 token。")
            mark_expired_and_regenerate(exp_dt)
            sys.exit(2)
        print(f"[错误] HTTP {e.code}：{e.reason}")
        sys.exit(2)
    except Exception as e:
        print(f"[错误] 请求失败：{e}")
        sys.exit(3)

    resp["fetchTime"] = bj_now().strftime("%Y-%m-%d %H:%M")
    resp["tokenExp"] = exp_dt.strftime("%Y-%m-%d %H:%M") if exp_dt else ""
    resp["tokenExpired"] = False
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(resp, f, ensure_ascii=False, indent=2)
    print(f"[OK] 已拉取 {begin}~{end} 排期，保存至 {OUT_JSON}，最近获取：{resp['fetchTime']}")
    regenerate()


if __name__ == "__main__":
    fetch()
