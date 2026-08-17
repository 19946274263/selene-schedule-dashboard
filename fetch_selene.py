# -*- coding: utf-8 -*-
"""从 Selene 实时拉取人力排期数据，保存快照并重新生成看板。

用法：
  # 方式一：环境变量传入 token
  set SELENE_TOKEN=xxxx
  python fetch_selene.py

  # 方式二：把 token 写入同目录 selene_token.txt（不要提交到公开仓库）
  python fetch_selene.py

  # 每小时自动刷新（Windows 任务计划）：用 schtasks 指向本脚本即可
  # 线上托管：腾讯云开发静态托管（稳定、独立干净域名），需先 `tcb login` 或配置 API Key

token 获取：登录 Selene 网页后，从浏览器 DevTools → Application → Local Storage →
  http://selene.hd123.cn:52163  → 找到 vuex 里的 token 字段复制。
注意：Selene token 会过期（通常 24 小时），过期后脚本会标记「token 已过期」并沿用旧数据，
  需重新从浏览器取一次 token 再运行。
"""
import os, sys, json, datetime, base64, urllib.request, urllib.error, subprocess, shutil, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
API = "http://selene.hd123.cn:52163/selene/v1/plan/gantt/employee/query"
OUT_JSON = os.path.join(HERE, "gantt_live.json")
STATIC_JSON = os.path.join(HERE, "gantt_0814_0821.json")
DEPLOY_HTML = os.path.join(HERE, "deploy", "index.html")
DEPLOY_DIR = os.path.join(HERE, "deploy")
GEN_HTML = os.path.join(HERE, "刘莹_人力排期看板.html")
LAST_STATE = os.path.join(HERE, "last_fetch_state.txt")

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


def window_days():
    today = bj_now().date()
    begin = today - datetime.timedelta(days=2)
    end = today + datetime.timedelta(days=4)
    f = lambda d: d.strftime("%Y-%m-%d")
    return f(begin), f(end)


def copy_to_deploy():
    try:
        os.makedirs(os.path.dirname(DEPLOY_HTML), exist_ok=True)
        shutil.copyfile(GEN_HTML, DEPLOY_HTML)
        print(f"[OK] 已同步到部署目录 {DEPLOY_HTML}")
    except Exception as e:
        print(f"[提示] 部署目录同步跳过：{e}")


def regenerate():
    print("[信息] 重新生成看板 HTML…")
    subprocess.run([sys.executable, os.path.join(HERE, "gen_dashboard_v2.py")], check=True)


# 线上托管环境：腾讯云开发静态托管（稳定、独立干净域名，规避共享域名被标记/回收）
CLOUDBASE_ENV = "ordering-app-d9gxw51o637a01eed"
CLOUDBASE_DOMAIN = "ordering-app-d9gxw51o637a01eed-1309857701.tcloudbaseapp.com"


def find_tcb():
    """定位 tcb 可执行文件：优先系统 PATH，其次 workbuddy 内置 node 工具目录（本机 tcb 实际位置）。"""
    p = shutil.which("tcb") or shutil.which("tcb.cmd")
    if p:
        return p
    base = os.path.join(os.path.expanduser("~"), ".workbuddy", "binaries",
                        "node", "cli-connector-packages")
    for name in ("tcb.cmd", "tcb"):
        cand = os.path.join(base, name)
        if os.path.exists(cand):
            return cand
    return None


def tcb_logged_in(tcb):
    """快速探测 tcb 是否已登录：tcb env list 未登录时立即返回错误且不卡。"""
    try:
        r = subprocess.run(f'"{tcb}" env list', shell=True,
                           capture_output=True, text=True, timeout=25, input="")
        out = (r.stdout + r.stderr)
        if "No valid identity" in out or r.returncode != 0:
            return False
        return True
    except Exception:
        return False


def deploy_cloudbase():
    """把部署目录推送到 CloudBase 静态托管。未登录/未安装/失败时仅告警不中断（优雅降级）。"""
    if not os.path.isdir(DEPLOY_DIR):
        print("[提示] 部署目录不存在，跳过 CloudBase 推送。")
        return
    tcb = find_tcb()
    if not tcb:
        print("[提示] 未找到 tcb CLI，跳过 CloudBase 推送（本地数据已更新；如需自动推送请先安装并登录 tcb）。")
        return
    if not tcb_logged_in(tcb):
        print("[提示] tcb 未登录，跳过 CloudBase 推送（本地数据已更新；如需自动推送请先 `tcb login` 或配置 API Key）。")
        return
    try:
        cmd = f'"{tcb}" hosting deploy "{DEPLOY_DIR}" -e {CLOUDBASE_ENV}'
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120, input="")
        if r.returncode == 0:
            print(f"[OK] 已推送到 CloudBase 静态托管：https://{CLOUDBASE_DOMAIN}/index.html")
        else:
            out = (r.stdout + r.stderr).strip()
            print(f"[提示] CloudBase 推送失败（不影响本地数据）：{out[:200]}")
    except subprocess.TimeoutExpired:
        print("[提示] CloudBase 推送超时（不影响本地数据），请稍后手动重试。")
    except Exception as e:
        print(f"[提示] CloudBase 推送跳过（{e}），本地数据已更新。")


def deploy_local():
    copy_to_deploy()
    deploy_cloudbase()



def stable_hash(obj):
    s = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def compute_state(payload):
    """任务数据 + 刷新状态指纹，用于差异比对（fetchTime 不计入，避免每次都变）。"""
    tokenExpired = payload.get("tokenExpired") if isinstance(payload, dict) else None
    tokenExp = payload.get("tokenExp") if isinstance(payload, dict) else None
    data = payload.get("data") if isinstance(payload, dict) else None
    tasks = data
    if isinstance(data, dict):
        try:
            tasks = data["employees"][0]["tasks"]
        except Exception:
            tasks = data
    return stable_hash({"tasks": tasks, "tokenExpired": tokenExpired,
                        "tokenExp": tokenExp})


def load_state():
    try:
        return open(LAST_STATE, encoding="utf-8").read().strip()
    except Exception:
        return ""


def save_state(s):
    try:
        with open(LAST_STATE, "w", encoding="utf-8") as f:
            f.write(s)
    except Exception:
        pass


def deploy_if_changed(state):
    """数据或刷新状态有变化才重新生成并部署，否则跳过（节省 CloudStudio 部署次数）。"""
    last = load_state()
    if state != last:
        regenerate()
        deploy_local()
        save_state(state)
        return True
    print("[信息] 数据无变化，跳过重新生成与部署（节省 CloudStudio 部署次数）。")
    return False


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
        if deploy_if_changed(compute_state(d)):
            print(f"[信息] token 已过期，已重新生成并部署「刷新失败」提示。")
        else:
            print(f"[信息] token 过期状态未变，跳过部署。")
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

    begin, end = window_days()
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
    if deploy_if_changed(compute_state(resp)):
        print(f"[OK] 数据有变化，已重新生成并部署看板。")


if __name__ == "__main__":
    fetch()
