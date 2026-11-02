"""下载 Maasea YouTube 响应脚本，打补丁去掉首页赞助卡片。

原版问题：首页卡片只按“是否含 pagead”判断，并把结论按字段号 / 模板名永久缓存在
$persistentStore 的 YouTubeAdvertiseInfo 里。一类赞助卡片不含 pagead，第一次被判成正常后，
同类卡片就一直留在首页（Maasea/sgmodule issue #89）。

改动：
1. 脚本前拼接 youtube_homefeed.js：/browse 在 Maasea 解析前先删掉首页赞助卡片；
   只有预过滤改了内容、Maasea 自己没改时，也要把预过滤结果写回；
2. 广告判断补上 aboutthisad 特征；
3. 不再使用“判过一次就记住”的白名单 / 黑名单，每张卡片都按内容判断；
4. 缓存版本号改为 1.0-clash，旧缓存自动作废，不需要手动清理。

用法: patch_youtube.py <dist目录>
"""
import os
import re
import sys
import time
import urllib.request

SRC = "https://raw.githubusercontent.com/Maasea/sgmodule/master/Script/Youtube/youtube.response.js"
dist = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))


def fetch(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read().decode("utf-8")
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(3)


def patch(code, name, pattern, repl):
    code, n = re.subn(pattern, repl, code)
    if n != 1:
        sys.exit(f"youtube.response.js: 补丁「{name}」匹配到 {n} 处（应为 1），上游写法变了，需人工检查")
    return code


code = fetch(SRC)
build = re.match(r"// Build: (.+)", code)
build = build.group(1).strip() if build else "未知"

# 广告判断：原函数改名保留，新函数 = 原判断（pagead）或含 aboutthisad
m = re.search(r"function (\w+)\((\w)\)\{if\(\2\.length<1e3\)return!1;let \w=\[112,97,103,101,97,100\]", code)
if not m:
    sys.exit("youtube.response.js: 找不到 pagead 判断函数，上游写法变了，需人工检查")
ni = m.group(1)
code = patch(code, "aboutthisad", rf"function {ni}\((\w)\)\{{if\(",
             rf"function {ni}(\1){{return {ni}__pagead(\1)||\1.length>=1e3&&globalThis.__clashAboutAd(\1)}}"
             rf"function {ni}__pagead(\1){{if(")

# 按字段号判断：去掉白名单 / 黑名单，只看内容
code = patch(code, "字段号不缓存",
             r"function (\w+)\((\w),(\w)\)\{let (\w)=\2\.no;if\(\3\.whiteNo\.includes\(\4\)\)return!1;"
             r"if\(\3\.blackNo\.includes\(\4\)\)return!0;let (\w)=" + ni + r"\(\2\.data\);"
             r"return \5\?\3\.blackNo\.push\(\4\):\3\.whiteNo\.push\(\4\),\3\.dirty=!0,\5\}",
             rf"function \1(\2,\3){{return {ni}(\2.data)}}")

# 按模板名判断：去掉白名单与学习，保留内置黑名单和 shorts 规则
code = patch(code, "模板名不缓存",
             r"if\((\w)\.whiteEml\.includes\((\w)\)\)(\w)=!1;else if\(\1\.blackEml\.includes\(\2\)\|\|"
             r"(/shorts\(\?!_pivot_item\)/)\.test\(\2\)\)\3=!0;else\{let (\w)=(\w)\?\.videoInfo\?\.videoContext\?\.videoContent;"
             r"\5&&\(\3=(\w+)\(\5\),\3\?\1\.blackEml\.push\(\2\):\1\.whiteEml\.push\(\2\),\1\.dirty=!0\)\}",
             r"if(\1.blackEml.includes(\2)||\4.test(\2))\3=!0;else{let \5=\6?.videoInfo?.videoContext?.videoContent;\5&&(\3=\7(\5))}")

# 缓存版本号：旧的 YouTubeAdvertiseInfo 自动作废
code = patch(code, "缓存版本", r'var (\w+)="1\.0";function (\w+)\(\)\{return\{whiteNo:',
             r'var \1="1.0-clash";function \2(){return{whiteNo:')

# 主流程：先跑预过滤，Maasea 不改时也写回预过滤结果
code = patch(code, "预过滤输入", r",(\w)=(\w+)\(\{url:(\w)\.request\.url,bodyBytes:\3\.response\.bodyBytes,",
             r",__hf=globalThis.__clashHomeFeed(\3.request.url,\3.response.bodyBytes),\1=\2({url:\3.request.url,bodyBytes:__hf.bytes,")
code = patch(code, "预过滤写回", r'(\w)\.action==="body"&&\1\.bodyBytes\?(\w)\.done\(\{bodyBytes:\1\.bodyBytes\}\):\2\.exit\(\)',
             r'\1.action==="body"&&\1.bodyBytes?\2.done({bodyBytes:\1.bodyBytes}):__hf.changed?\2.done({bodyBytes:__hf.bytes}):\2.exit()')

prelude = open(os.path.join(here, "youtube_homefeed.js"), encoding="utf-8").read()
header = (f"// 修改说明：基于 Maasea/sgmodule youtube.response.js（Build: {build}），拼接首页赞助卡片预过滤，"
          f"广告判断补 aboutthisad、不再缓存判定结果；原作者与许可证见 https://github.com/Maasea/sgmodule （Apache-2.0）\n")
os.makedirs(os.path.join(dist, "youtube"), exist_ok=True)
with open(os.path.join(dist, "youtube", "youtube.response.js"), "w", encoding="utf-8") as f:
    f.write(header + prelude + "\n" + code)
print(f"Maasea youtube.response.js（Build: {build}）: 补丁全部应用")
