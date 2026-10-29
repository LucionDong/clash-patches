"""把 Surge 模块改成 Clash 更稳的写法：参数占位符写死、去掉 engine=webview、按正则删行。

用法: sgmodule_fix.py <输入> <输出> <新模块名> [--set 参数=值 ...] [--drop 正则 ...]
"""
import argparse
import re

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("dst")
ap.add_argument("name")
ap.add_argument("--set", action="append", default=[])
ap.add_argument("--drop", action="append", default=[])
a = ap.parse_args()

text = open(a.src, encoding="utf-8").read()
m = re.search(r"^#!arguments\s*=\s*(.+)$", text, re.M)
args = {k: v.strip('"') for k, v in re.findall(r'([\w.]+):("[^"]*"|[^,]*)', m.group(1))} if m else {}
for kv in a.set:
    k, v = kv.split("=", 1)
    args[k] = v

out, dropped = [], []
for line in text.splitlines():
    if line.startswith("#!name"):
        line = f"#!name = {a.name}"
    elif line.startswith(("#!arguments", "#!openUrl")):
        continue  # 参数已写死，不再暴露给客户端
    elif any(re.search(p, line) for p in a.drop):
        dropped.append(line.split("=", 1)[0].strip() if "=" in line else line[:60])
        continue
    line = re.sub(r"\{\{\{([\w.]+)\}\}\}", lambda x: args[x.group(1)], line)
    line = re.sub(r",\s*engine=webview", "", line)
    out.append(line)

open(a.dst, "w", encoding="utf-8").write("\n".join(out) + "\n")
left = sum("{{{" in l for l in out)
print(f"dropped={len(dropped)} {dropped} unresolved_placeholders={left}")
