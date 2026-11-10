# clash-patches

给 clash.md（mihomo 内核 iOS 客户端）用的去广告模块。GitHub Actions 每天北京时间 04:00 从上游拉取并重新生成 `dist/`，Clash 里用「链接」添加即可自动跟随更新。

| 模块 | 链接 | 来源 |
|---|---|---|
| 合并去广告（App 清单见 `apps.txt`） | `https://raw.githubusercontent.com/LucionDong/clash-patches/main/dist/MyAdBlock.sgmodule` | fmz200/wool_scripts 分 App 模块 + 墨鱼 amdc.js |
| 微博 | `https://raw.githubusercontent.com/LucionDong/clash-patches/main/dist/WeiboAds.sgmodule` | ddgksf2013 WeiboAds.conf 转 Surge 格式 |
| B站去广告 | `https://raw.githubusercontent.com/LucionDong/clash-patches/main/dist/BiliADBlock.sgmodule` | Biliverse/ADBlock 最新版，脚本经修补（见 `scripts/patch_biliverse.py`） |
| B站界面增强（小火箭） | `https://raw.githubusercontent.com/LucionDong/clash-patches/main/dist/BiliEnhanced.srmodule` | Biliverse/Enhanced 最新版小火箭模块，脚本拼接 TextDecoder polyfill（见 `scripts/patch_enhanced.py`）；首页标签与底栏写死在模块参数里（`TAB_ARGUMENT`：推荐/热门/追番，首页/动态/我的），设置面板在小火箭里用不了 |
| B站开屏补丁 | `https://raw.githubusercontent.com/LucionDong/clash-patches/main/dist/BiliSplash.sgmodule` | 手写（`static/`） |
| YouTube | `https://raw.githubusercontent.com/LucionDong/clash-patches/main/dist/YouTube.sgmodule` | 墨鱼规则移植（`static/`）+ Maasea 响应脚本修补版（`scripts/patch_youtube.py`：首页赞助卡片预过滤、广告判断不再缓存） |
| YouTube get_watch 回退实验 | `https://raw.githubusercontent.com/LucionDong/clash-patches/main/dist/YouTube-GetWatchTest.sgmodule` | 手写（`static/`），实验用：get_watch 本地返回 404，看 App 是否改走 player + next；须与 YouTube 模块同时启用，播放异常就关掉 |

- 加 App：在 `apps.txt` 加一行 `partX/模块名`（名称见 fmz200/wool_scripts 的 `Surge/module/split/`），推送后自动重建。
- 手动重建：Actions → build → Run workflow。
- 某个目标构建失败时保留上一次的产物，并在 Actions 里标红。
- 自动放行：开屏这类接口靠响应脚本把广告改成过期，App 才会刷新本地缓存；如果域名同时在配置的 anti-AD 里，请求会被拒绝、脚本不运行，App 一直用旧缓存。构建最后一步 `scripts/pass_script_hosts.py` 找出这类域名，在所属模块的 `[Rule]` 开头加 `DOMAIN,…,DIRECT`（模块规则优先于配置规则），清单见 `dist/script-pass-hosts.txt`。模块里已有显式规则的域名、通配 pattern 不处理；anti-AD 下载失败时沿用上一次的清单。
