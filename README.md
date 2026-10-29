# clash-patches

给 clash.md（mihomo 内核 iOS 客户端）用的去广告模块。GitHub Actions 每天北京时间 04:00 从上游拉取并重新生成 `dist/`，Clash 里用「链接」添加即可自动跟随更新。

| 模块 | 链接 | 来源 |
|---|---|---|
| 合并去广告（App 清单见 `apps.txt`） | `https://raw.githubusercontent.com/LucionDong/clash-patches/main/dist/MyAdBlock.sgmodule` | fmz200/wool_scripts 分 App 模块 + 墨鱼 amdc.js |
| 微博 | `https://raw.githubusercontent.com/LucionDong/clash-patches/main/dist/WeiboAds.sgmodule` | ddgksf2013 WeiboAds.conf 转 Surge 格式 |
| B站去广告 | `https://raw.githubusercontent.com/LucionDong/clash-patches/main/dist/BiliADBlock.sgmodule` | Biliverse/ADBlock 最新版，脚本经修补（见 `scripts/patch_biliverse.py`） |
| B站开屏补丁 | `https://raw.githubusercontent.com/LucionDong/clash-patches/main/dist/BiliSplash.sgmodule` | 手写（`static/`） |
| YouTube | `https://raw.githubusercontent.com/LucionDong/clash-patches/main/dist/YouTube.sgmodule` | 墨鱼规则移植 + Maasea 响应脚本（`static/`） |

- 加 App：在 `apps.txt` 加一行 `partX/模块名`（名称见 fmz200/wool_scripts 的 `Surge/module/split/`），推送后自动重建。
- 手动重建：Actions → build → Run workflow。
- 某个目标构建失败时保留上一次的产物，并在 Actions 里标红。
