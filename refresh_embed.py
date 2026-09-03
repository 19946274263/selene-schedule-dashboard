#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, re, urllib.request, sys

HTML = "cloud_check.html"
PROXY = "https://ordering-app-d9gxw51o637a01eed.service.tcloudbase.com/seleneProxy"

# 1) 拉取代理最新 payload
req = urllib.request.Request(PROXY, headers={"Cache-Control": "no-store"})
with urllib.request.urlopen(req, timeout=30) as r:
    payload = json.loads(r.read().decode("utf-8"))

if payload.get("tokenExpired"):
    print("ERROR: 代理返回 tokenExpired=true，token 可能已过期，未替换内嵌 D")
    sys.exit(2)

print("代理返回: empName=%s sprint=%s tasks=%d lastFetch=%s tokenExp=%s" % (
    payload.get("empName"), payload.get("sprint"),
    len(payload.get("tasks", [])), payload.get("lastFetch"), payload.get("tokenExp")))

# 2) 读 html，替换 let D = {...};  （以 tokenExpired 字段为终止锚点，避免任务摘要里的字符误截断）
with open(HTML, "r", encoding="utf-8") as f:
    content = f.read()

pattern = re.compile(r'let D = \{.*?tokenExpired": (?:true|false)\};', re.S)
m = pattern.search(content)
if not m:
    print("ERROR: 未找到内嵌 let D 锚点")
    sys.exit(3)

new_d = "let D = " + json.dumps(payload, ensure_ascii=False) + ";"
new_content = pattern.sub(new_d, content, count=1)
if new_content == content:
    print("ERROR: 替换未发生")
    sys.exit(4)

with open(HTML, "w", encoding="utf-8") as f:
    f.write(new_content)

print("OK: 已用最新 payload 刷新内嵌 D（lastFetch=%s）" % payload.get("lastFetch"))
