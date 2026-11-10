"""下载 Biliverse Enhanced 最新版小火箭模块，生成脚本可用的修补版。

小火箭的脚本环境没有 TextDecoder，官方 request/response 脚本一运行就报
ReferenceError: Can't find variable: TextDecoder，底栏、顶栏、我的页都不生效（日志 2026-11-10）。

改动：
1. request/response 脚本前拼接 TextDecoder/TextEncoder polyfill（宿主已有时不生效）；
2. gRPC 解压在 $utils 不可用时退回脚本内置 pako（同 patch_biliverse.py）；
3. 模块 script-path 指向本仓库 dist/biliverse/ 下的修补版脚本；config 脚本与设置面板不用 TextDecoder，保持官方地址；
4. 首页标签与底栏写进 tab/v2 脚本的参数：设置面板要在 B站 App 的 WebView 里运行，
   而 App 内入口 app.bilibili.com/settings/ 在小火箭里 Map Local 返回空，面板用不了（日志 2026-11-10）。

用法: patch_enhanced.py <dist目录> <raw地址前缀>
"""
import os
import re
import sys
import time
import urllib.request

dist, raw_base = sys.argv[1], sys.argv[2].rstrip("/")
here = os.path.dirname(os.path.abspath(__file__))
REL = "https://github.com/Biliverse/Enhanced/releases"


def fetch(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read().decode("utf-8")
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(3)


module = fetch(f"{REL}/latest/download/Biliverse.Enhanced.srmodule")
version = re.search(r"^#!version\s*=\s*(\S+)", module, re.M).group(1)
polyfill = open(os.path.join(here, "textcodec_polyfill.js"), encoding="utf-8").read()
UNGZIP = re.compile(r"return \$utils\.ungzip\((\w+)\);default:return (\w+)\.ungzip\(\1\)")
# 首页标签 2037 推荐、780 热门、545 追番，默认停在推荐；底栏 首页、动态、我的（id 见脚本内 RegionList 与 Tab.bottom）
# 逗号写成 %2C：小火箭按逗号切分脚本行，参数在第一个逗号处被截断（日志 2026-11-10 18:07）；脚本解析参数时会先 URL 解码
TAB_ARGUMENT = 'Home.Tab="2037%2C780%2C545"&Home.Tab_default="2037"&Bottom="home%2Cdynamic%2Cmine"'

os.makedirs(os.path.join(dist, "biliverse"), exist_ok=True)
for kind in ("request", "response"):
    code = fetch(f"{REL}/download/v{version}/{kind}.bundle.js")
    if "TextDecoder" not in code:
        sys.exit(f"{kind}.bundle.js v{version}: 不再使用 TextDecoder，确认后可以改回官方脚本")
    m = UNGZIP.search(code)
    if not m:
        sys.exit(f"{kind}.bundle.js v{version}: 找不到 $utils.ungzip 调用，上游写法变了，需人工检查")
    v, fb = m.group(1), m.group(2)
    safe = (f'{{try{{const __r=typeof $utils!="undefined"&&$utils.ungzip?$utils.ungzip({v}):null;'
            f'if(__r&&__r.length)return __r}}catch(__e){{}}return {fb}.ungzip({v})}}'
            f'default:return {fb}.ungzip({v})')
    code = code[:m.start()] + safe + code[m.end():]
    header = (f"// 修改说明：在 Biliverse/Enhanced v{version} 原版 {kind}.bundle.js 前拼接 TextDecoder/TextEncoder polyfill，"
              f"并把 gRPC 解压改为 $utils 不可用时退回内置 pako；原作者与许可证见 https://github.com/Biliverse/Enhanced （Apache-2.0）\n")
    with open(os.path.join(dist, "biliverse", f"Enhanced_{kind}.bundle.js"), "w", encoding="utf-8") as f:
        f.write(header + polyfill + "\n" + code)

text, n = re.subn(rf"{re.escape(REL)}/download/v[^/]+/(request|response)\.bundle\.js",
                  lambda m: f"{raw_base}/biliverse/Enhanced_{m.group(1)}.bundle.js", module)
if n == 0:
    sys.exit("模块里没有找到 Enhanced 脚本地址，上游写法变了，需人工检查")
text, na = re.subn(r"^(Biliverse\.Enhanced\.x\.resource\.show\.tab\.v2 = .*, argument=)$",
                   lambda m: m.group(1) + TAB_ARGUMENT, text, flags=re.M)
if na != 1:
    sys.exit(f"tab/v2 脚本行（参数为空）找到 {na} 处（应为 1），上游写法变了，需人工检查")
text, nn = re.subn(r"^(#!name\s*=\s*.+)$", r"\1[TextDecoder 修补版]", text, count=1, flags=re.M)
if nn != 1:
    sys.exit("模块里没有 #!name，上游写法变了，需人工检查")
with open(os.path.join(dist, "BiliEnhanced.srmodule"), "w", encoding="utf-8") as f:
    f.write(text)
print(f"Biliverse Enhanced v{version}: 替换脚本地址 {n} 处，写入首页标签与底栏参数")
