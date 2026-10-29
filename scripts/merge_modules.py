"""把奶思按 App 拆分的 Surge 模块合并成一个，参数占位符直接替换成默认值。"""
import re
import sys
import time
import urllib.request

BASE = "https://raw.githubusercontent.com/fmz200/wool_scripts/main/Surge/module/split/"
out_path = sys.argv[1]
apps = sys.argv[2:]  # 形如 partT/Taobao

ORDER = ["Rule", "URL Rewrite", "Header Rewrite", "Body Rewrite", "Map Local", "Script"]
sections = {k: [] for k in ORDER}
hosts, skipped = [], []
AMDC = ('amdc = type=http-response, pattern="^http:\\/\\/[a-zA-Z0-9_-]+(\\.[a-zA-Z0-9_-]+){1,4}(:\\d+)?\\/amdc\\/mobileDispatch", '
        "requires-body=1, timeout=10, script-path=https://raw.githubusercontent.com/ddgksf2013/Scripts/refs/heads/master/amdc.js")



def fetch(url, tries=3):
    for i in range(tries):
        try:
            return urllib.request.urlopen(url, timeout=30).read().decode("utf-8")
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(3)


for app in apps:
    text = fetch(BASE + app + ".sgmodule")
    m = re.search(r"^#!arguments\s*=\s*(.+)$", text, re.M)
    args = dict(kv.split(":", 1) for kv in m.group(1).split(",")) if m else {}
    name = re.search(r"^#!name\s*=\s*(.+)$", text, re.M).group(1).strip()
    cur = None
    for line in text.splitlines():
        s = line.strip()
        h = re.match(r"^\[(.+)\]$", s)
        if h:
            cur = h.group(1)
            if cur not in sections and cur != "MITM":
                skipped.append(f"{name}: [{cur}]")
            if cur in sections:
                sections[cur].append(f"# --- {name} ---")
            continue
        if not s or s.startswith("#!"):
            continue
        if cur == "MITM" and s.startswith("hostname"):
            hosts += [x.strip() for x in s.split("=", 1)[1].replace("%APPEND%", "").split(",") if x.strip()]
            continue
        if cur in sections:
            for k, v in args.items():
                s = s.replace("{{{%s}}}" % k.strip(), v.strip().strip('"'))
            if "{{{" in s:
                skipped.append(f"{name}: 未替换参数 {s[:60]}")
            sections[cur].append(s)

seen, body = set(), []
for k in ORDER:
    lines = [l for l in sections[k] if l.startswith("#") or not (l in seen or seen.add(l))]
    if k == "Script":
        lines += ["# --- 阿里系 AMDC 处理（墨鱼） ---", AMDC]
    if any(not l.startswith("#") for l in lines):
        body += [f"[{k}]"] + lines + [""]
out = ["#!name=我的去广告合集", "#!desc=奶思分 App 模块合并：" + "、".join(a.split("/")[1] for a in apps) + " + 阿里系AMDC", ""]
out += body + ["[MITM]", "hostname = %APPEND% " + ", ".join(dict.fromkeys(hosts)), ""]
open(out_path, "w", encoding="utf-8").write("\n".join(out))
cnt = {k: sum(1 for l in sections[k] if not l.startswith("#")) for k in ORDER}
print(cnt, "hosts", len(dict.fromkeys(hosts)), "skipped", skipped)
