"""下载 Biliverse ADBlock 最新版，生成 Clash 可用的模块和脚本。

改动：
1. 脚本前拼接 TextDecoder/TextEncoder polyfill（宿主已有时不生效）；
2. gRPC 解压在 $utils 不可用时退回脚本内置 pako（Clash 下横幅等 gRPC 接口失效的根因）；
3. 模块参数写死、去掉 engine=webview、删除评论区脚本（评论区加载慢）；
4. 模块 script-path 指向本仓库 dist/ 下的修补版脚本。

用法: patch_biliverse.py <dist目录> <raw地址前缀>
"""
import os
import re
import subprocess
import sys
import time
import urllib.request

dist, raw_base = sys.argv[1], sys.argv[2].rstrip("/")
here = os.path.dirname(os.path.abspath(__file__))
REL = "https://github.com/Biliverse/ADBlock/releases"


def fetch(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read().decode("utf-8")
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(3)


module = fetch(f"{REL}/latest/download/BiliBili.ADBlock.sgmodule")
version = re.search(r"^#!version\s*=\s*(\S+)", module, re.M).group(1)
polyfill = open(os.path.join(here, "textcodec_polyfill.js"), encoding="utf-8").read()
UNGZIP = re.compile(r"return \$utils\.ungzip\((\w+)\);default:return (\w+)\.ungzip\(\1\)")

os.makedirs(os.path.join(dist, "biliverse"), exist_ok=True)
for kind in ("request", "response"):
    code = fetch(f"{REL}/download/v{version}/{kind}.bundle.js")
    m = UNGZIP.search(code)
    if not m:
        sys.exit(f"{kind}.bundle.js v{version}: 找不到 $utils.ungzip 调用，上游写法变了，需人工检查")
    v, fb = m.group(1), m.group(2)
    safe = (f'{{try{{const __r=typeof $utils!="undefined"&&$utils.ungzip?$utils.ungzip({v}):null;'
            f'if(__r&&__r.length)return __r}}catch(__e){{}}return {fb}.ungzip({v})}}'
            f'default:return {fb}.ungzip({v})')
    code = code[:m.start()] + safe + code[m.end():]
    header = (f"// 修改说明：在 Biliverse/ADBlock v{version} 原版 {kind}.bundle.js 前拼接 TextDecoder/TextEncoder polyfill，"
              f"并把 gRPC 解压改为 $utils 不可用时退回内置 pako；原作者与许可证见 https://github.com/Biliverse/ADBlock （Apache-2.0）\n")
    with open(os.path.join(dist, "biliverse", f"ADBlock_{kind}.bundle.js"), "w", encoding="utf-8") as f:
        f.write(header + polyfill + "\n" + code)

src = os.path.join(dist, "biliverse", ".ADBlock.orig.sgmodule")
out = os.path.join(dist, "BiliADBlock.sgmodule")
open(src, "w", encoding="utf-8").write(module)
subprocess.run([sys.executable, "-I", os.path.join(here, "sgmodule_fix.py"), src, out,
                "B站去广告[Clash版]", "--set", "Storage=Argument", "--set", "Reply.AD=false",
                "--drop", r"ADBlock\.reply"], check=True)
os.remove(src)

text = open(out, encoding="utf-8").read()
text, n = re.subn(rf"{re.escape(REL)}/download/v[^/]+/(request|response)\.bundle\.js",
                  lambda m: f"{raw_base}/biliverse/ADBlock_{m.group(1)}.bundle.js", text)
if n == 0:
    sys.exit("模块里没有找到 Biliverse 脚本地址，上游写法变了，需人工检查")
text = text.replace("#!name = B站去广告[Clash版]", f"#!name = B站去广告[Clash版]\n#!version = {version}", 1)
open(out, "w", encoding="utf-8").write(text)
print(f"Biliverse ADBlock v{version}: 替换脚本地址 {n} 处")
