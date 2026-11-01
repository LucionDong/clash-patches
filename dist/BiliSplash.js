// B站开屏列表：放行服务器真实响应，把其中的素材改成 2040 年才生效、时长 0，
// 让客户端用同 ID 覆盖本地缓存，已缓存的开屏素材就永远到不了排期。
const FAR = 2240150400; // 2040-12-27
const path = $request.url.replace(/^https?:\/\/[^/]+/, "").split("?")[0];
let obj;
try {
  obj = JSON.parse($response.body);
} catch (e) {}
if (!obj || typeof obj !== "object") {
  console.log(`[BiliSplash] ${path} 非 JSON，原样放行`);
  $done({});
} else {
  const d = obj.data && typeof obj.data === "object" ? obj.data : {};
  const list = Array.isArray(d.list) ? d.list : [];
  // 诊断：真实响应结构，便于下次从日志判断
  console.log(`[BiliSplash] ${path} code=${obj.code} keys=${Object.keys(d).join(",")} list=${list.length} show=${Array.isArray(d.show) ? d.show.length : d.show} keep_ids=${JSON.stringify(d.keep_ids || null).slice(0, 300)}`);
  if (list[0]) console.log(`[BiliSplash] list[0] ${JSON.stringify(list[0]).slice(0, 600)}`);

  const ids = [];
  for (const item of list) {
    if (!item || typeof item !== "object") continue;
    item.duration = 0;
    item.begin_time = FAR;
    item.end_time = FAR;
    if (item.id !== undefined) ids.push(item.id);
  }
  if ("show" in d) d.show = [];
  if ("event_list" in d) d.event_list = [];
  d.keep_ids = ids;
  d.max_time = 0;
  d.min_interval = 31536000;
  d.pull_interval = 31536000;
  obj.data = d;
  console.log(`[BiliSplash] ${path} 已置为过期 ${list.length} 条，keep_ids=${ids.length}`);
  $done({ body: JSON.stringify(obj) });
}
