#!/usr/bin/env bash
# 生成 dist/ 下的 Clash 模块。单个目标失败不影响其他目标，失败的目标保留上一次的产物。
set -u
cd "$(dirname "$0")"

RAW_BASE="https://raw.githubusercontent.com/LucionDong/clash-patches/main/dist"
DIST=dist
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$DIST"
failed=()

# 构建一个目标：先写到临时目录，成功后再覆盖 dist
build() {
  local name=$1; shift
  echo "==> $name"
  if "$@"; then
    echo "    ok"
  else
    echo "    FAILED，保留上一次的产物"
    failed+=("$name")
  fi
}

merge_apps() {
  python3 -I scripts/merge_modules.py "$TMP/MyAdBlock.sgmodule" $(grep -vE '^\s*(#|$)' apps.txt) \
    && cp "$TMP/MyAdBlock.sgmodule" "$DIST/"
}

# 开屏接口由 weibo_json.js 把素材改成过期，响应必须到达 App 才能刷新本地缓存；
# 这两个域名在 anti-AD 里，配置的 RULE-SET,anti_ad,REJECT 会让脚本永远不运行，这里用模块规则放行
WEIBO_PASS_DOMAINS="bootpreload.uve.weibo.com wbapp.uve.weibo.com"

weibo() {
  curl -fsSL --retry 3 -o "$TMP/WeiboAds.conf" \
      https://raw.githubusercontent.com/ddgksf2013/Rewrite/master/AdBlock/WeiboAds.conf \
    && python3 -I scripts/qxrw2sgmodule.py "$TMP/WeiboAds.conf" "$TMP/WeiboAds.raw.sgmodule" '微博净化[墨鱼版·Surge格式]' \
    && awk -v domains="$WEIBO_PASS_DOMAINS" '
         { print }
         $0 == "[Rule]" { n = split(domains, d, " "); for (i = 1; i <= n; i++) print "DOMAIN," d[i] ",DIRECT"; found = 1 }
         END { if (!found) { print "WeiboAds 缺少 [Rule] 段，无法放行开屏接口" > "/dev/stderr"; exit 1 } }
       ' "$TMP/WeiboAds.raw.sgmodule" > "$TMP/WeiboAds.sgmodule" \
    && cp "$TMP/WeiboAds.sgmodule" "$DIST/"
}

biliverse() {
  mkdir -p "$TMP/bili" \
    && python3 -I scripts/patch_biliverse.py "$TMP/bili" "$RAW_BASE" \
    && mkdir -p "$DIST/biliverse" \
    && cp "$TMP/bili/BiliADBlock.sgmodule" "$DIST/" \
    && cp "$TMP/bili/biliverse/"*.bundle.js "$DIST/biliverse/"
}

static_modules() {
  cp static/*.sgmodule static/*.js "$DIST/"
}

build "合并去广告模块" merge_apps
build "微博" weibo
build "B站去广告" biliverse
build "静态模块" static_modules

if ((${#failed[@]})); then
  echo "失败的目标: ${failed[*]}"
  exit 1
fi
