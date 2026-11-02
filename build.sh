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

youtube() {
  python3 -I scripts/patch_youtube.py "$DIST"
}

static_modules() {
  cp static/*.sgmodule static/*.js "$DIST/"
}

# 开屏等接口靠响应脚本把广告改成过期，App 才会刷新本地缓存；配置里的 anti-AD 会拒绝其中一些域名，
# 脚本就永远不运行。这里给每个模块补上放行规则（配置用的 mihomo.mrs 与 clash.yaml 同源同版本）。
# anti-ad.net 在 Cloudflare 后面，Actions 的机房 IP 可能被拦，先用 GitHub 上的同一份文件
script_pass() {
  curl -fsSL --retry 3 -o "$TMP/anti-ad.yaml" \
      https://raw.githubusercontent.com/privacy-protection-tools/anti-AD/master/anti-ad-clash.yaml \
    || curl -fsSL --retry 3 -o "$TMP/anti-ad.yaml" https://anti-ad.net/clash.yaml \
    || : > "$TMP/anti-ad.yaml"
  python3 -I scripts/pass_script_hosts.py "$TMP/anti-ad.yaml" "$DIST/script-pass-hosts.txt" "$DIST"/*.sgmodule
}

build "合并去广告模块" merge_apps
build "微博" weibo
build "B站去广告" biliverse
build "YouTube 脚本" youtube
build "静态模块" static_modules
build "放行被 anti-AD 拒绝的脚本接口" script_pass

if ((${#failed[@]})); then
  echo "失败的目标: ${failed[*]}"
  exit 1
fi
