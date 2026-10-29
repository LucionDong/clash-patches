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

weibo() {
  curl -fsSL --retry 3 -o "$TMP/WeiboAds.conf" \
      https://raw.githubusercontent.com/ddgksf2013/Rewrite/master/AdBlock/WeiboAds.conf \
    && python3 -I scripts/qxrw2sgmodule.py "$TMP/WeiboAds.conf" "$TMP/WeiboAds.sgmodule" '微博净化[墨鱼版·Surge格式]' \
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
  cp static/*.sgmodule "$DIST/"
}

build "合并去广告模块" merge_apps
build "微博" weibo
build "B站去广告" biliverse
build "静态模块" static_modules

if ((${#failed[@]})); then
  echo "失败的目标: ${failed[*]}"
  exit 1
fi
