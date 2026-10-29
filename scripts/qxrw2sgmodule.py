"""把无章节头的 QX 重写文件（墨鱼 WeiboAds.conf）转成带章节头的 Surge 模块。"""
import re
import sys

src, dst, name = sys.argv[1], sys.argv[2], sys.argv[3]

rules, url_rw, body_rw, map_local, scripts, hosts = [], [], [], [], [], []
unknown = []
JSON_HDR = 'header="Content-Type:application/json"'


def expand_host(h):
    # api.weibo.* 这种尾部通配不一定被支持，展开成 .cn/.com
    return [h[:-1] + "cn", h[:-1] + "com"] if h.endswith(".*") else [h]


for raw in open(src, encoding="utf-8"):
    l = raw.strip()
    if not l or l.startswith(("#", ";", "//")):
        continue
    if l.startswith("hostname"):
        for h in l.split("=", 1)[1].split(","):
            hosts += expand_host(h.strip())
        continue
    m = re.match(r"(host|host-suffix|host-keyword)\s*,\s*([^,]+?)\s*,\s*(\w+)$", l, re.I)
    if m:
        t = {"host": "DOMAIN", "host-suffix": "DOMAIN-SUFFIX", "host-keyword": "DOMAIN-KEYWORD"}[m[1].lower()]
        rules.append(f"{t},{m[2]},{m[3].upper()}")
        continue
    m = re.match(r"(\S+)\s+url\s+(\S+)\s*(.*)$", l)
    if not m:
        unknown.append(l)
        continue
    pat, act, arg = m[1], m[2], m[3].strip()
    if act == "script-response-body":
        p = f'"{pat}"' if "," in pat else pat
        scripts.append(f"weibo_{len(scripts) + 1} = type=http-response, pattern={p}, requires-body=1, max-size=-1, timeout=60, script-path={arg}")
    elif act == "reject-200":
        map_local.append(f'{pat} data-type=text data="" status-code=200')
    elif act == "reject-dict":
        map_local.append(f'{pat} data-type=text data="{{}}" status-code=200 {JSON_HDR}')
    elif act == "reject":
        url_rw.append(f"{pat} - reject")
    elif act == "jsonjq-response-body":
        body_rw.append(f"http-response-jq {pat} {arg}")
    else:
        unknown.append(l)

out = [f"#!name={name}", "#!desc=由墨鱼 QX 重写 WeiboAds.conf 转换为 Surge 模块格式", ""]
for title, body in [("Rule", rules), ("URL Rewrite", url_rw), ("Body Rewrite", body_rw),
                    ("Map Local", map_local), ("Script", scripts)]:
    if body:
        out += [f"[{title}]"] + body + [""]
seen = list(dict.fromkeys(hosts))
out += ["[MITM]", "hostname = %APPEND% " + ", ".join(seen), ""]
open(dst, "w", encoding="utf-8").write("\n".join(out))
print(f"rule={len(rules)} url_rewrite={len(url_rw)} body_rewrite={len(body_rw)} map_local={len(map_local)} script={len(scripts)} hosts={len(seen)} unknown={len(unknown)}")
for u in unknown:
    print("UNKNOWN:", u[:160])
