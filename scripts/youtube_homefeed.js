// YouTube 首页 /browse 赞助卡片预过滤：在 Maasea 解析前，直接在原始 protobuf 里删掉广告卡片。
// 识别特征参考 Hey-sayiwanna/YouTube-ADBlock-on-Feed 基于真实抓包的结论（代码为本仓库自写）：
// 首页卡片是 field 49399797 容器下的 field 1 / 32；含 www.youtube.com/aboutthisad 的直接判为广告，
// 否则命中两个及以上 pagead / doubleclick 广告链接特征才判为广告。
globalThis.__clashHomeFeed = (() => {
  const CONTAINER = 49399797;
  const ITEM_FIELDS = [1, 32];
  const MAX_DEPTH = 8;
  const enc = (s) => Uint8Array.from(s, (c) => c.charCodeAt(0));
  const ABOUT = enc("www.youtube.com/aboutthisad");
  const MARKERS = [
    "googleadservices.com/pagead/aclk",
    "www.youtube.com/pagead/adview",
    "www.youtube.com/pagead/interaction",
    "www.youtube.com/pagead/",
    "googleads.g.doubleclick.net/pagead/",
    "yt3.ggpht.com/proxy",
  ].map(enc);
  const DIVIDER = enc("cell_divider.eml-fe");

  function has(a, s, e, n) {
    const last = e - n.length;
    for (let i = s; i <= last; i++) {
      if (a[i] !== n[0]) continue;
      let j = 1;
      while (j < n.length && a[i + j] === n[j]) j++;
      if (j === n.length) return true;
    }
    return false;
  }

  function isAd(a, s, e) {
    if (has(a, s, e, ABOUT)) return true;
    let hits = 0;
    for (const m of MARKERS) if (has(a, s, e, m) && ++hits >= 2) return true;
    return false;
  }

  function varint(a, i, e) {
    let v = 0;
    let mul = 1;
    for (let k = 0; k < 8 && i < e; k++) {
      const b = a[i++];
      v += (b & 127) * mul;
      if (b < 128) return [v, i];
      mul *= 128;
    }
    return null;
  }

  function lenBytes(v) {
    const out = [];
    while (v >= 128) {
      out.push((v % 128) | 128);
      v = Math.floor(v / 128);
    }
    out.push(v);
    return Uint8Array.from(out);
  }

  // 把 [s, e) 当作 protobuf 消息逐字段解析；不是合法消息时返回 null
  function fields(a, s, e) {
    const out = [];
    let i = s;
    while (i < e) {
      const k = varint(a, i, e);
      if (!k) return null;
      const no = Math.floor(k[0] / 8);
      const wt = k[0] % 8;
      if (!no) return null;
      let ps = k[1];
      let pe;
      if (wt === 0) {
        const v = varint(a, ps, e);
        if (!v) return null;
        pe = v[1];
      } else if (wt === 1) pe = ps + 8;
      else if (wt === 5) pe = ps + 4;
      else if (wt === 2) {
        const v = varint(a, ps, e);
        if (!v) return null;
        ps = v[1];
        pe = ps + v[0];
      } else return null;
      if (pe > e) return null;
      out.push({ no, wt, start: i, keyEnd: k[1], ps, pe });
      i = pe;
    }
    return out;
  }

  // 给 Maasea 的广告判断补上 aboutthisad 特征（原版只认 pagead）
  globalThis.__clashAboutAd = (a) => ArrayBuffer.isView(a) && has(a, 0, a.length, ABOUT);

  const total = (parts) => parts.reduce((n, p) => n + p.length, 0);

  function filterContainer(a, s, e, stat) {
    const fs = fields(a, s, e);
    if (!fs) return null;
    const ad = fs.map((f) => {
      if (f.wt !== 2 || !ITEM_FIELDS.includes(f.no)) return false;
      stat.items++;
      return isAd(a, f.ps, f.pe);
    });
    const n = ad.filter(Boolean).length;
    if (!n) return null;
    stat.ads += n;
    // 广告卡片后面紧跟的分隔线一起删，避免留下空白条
    const drop = ad.map((x, i) => x || (i > 0 && ad[i - 1] && fs[i].wt === 2 && fs[i].no === 1 &&
      fs[i].pe - fs[i].ps <= 3000 && has(a, fs[i].ps, fs[i].pe, DIVIDER)));
    const parts = fs.filter((f, i) => !drop[i]).map((f) => a.subarray(f.start, f.pe));
    return { parts, len: total(parts) };
  }

  // 递归找容器；子消息有改动时重写它的长度前缀，返回 null 表示没有改动
  function rewrite(a, s, e, depth, stat) {
    const fs = fields(a, s, e);
    if (!fs) return null;
    let changed = false;
    const parts = [];
    for (const f of fs) {
      let child = null;
      if (f.wt === 2 && f.no === CONTAINER) child = filterContainer(a, f.ps, f.pe, stat);
      else if (f.wt === 2 && depth < MAX_DEPTH && f.pe - f.ps > 1) child = rewrite(a, f.ps, f.pe, depth + 1, stat);
      if (child) {
        parts.push(a.subarray(f.start, f.keyEnd), lenBytes(child.len), ...child.parts);
        changed = true;
      } else parts.push(a.subarray(f.start, f.pe));
    }
    return changed ? { parts, len: total(parts) } : null;
  }

  // 不用 instanceof：响应体可能来自宿主的另一个 JS 环境
  const asBytes = (b) => ArrayBuffer.isView(b) ? new Uint8Array(b.buffer, b.byteOffset, b.byteLength)
    : Object.prototype.toString.call(b) === "[object ArrayBuffer]" ? new Uint8Array(b) : null;

  return (url, body) => {
    const bytes = asBytes(body);
    if (!/\/youtubei\/v1\/browse/.test(url) || !bytes) return { bytes: body, changed: false };
    try {
      const stat = { items: 0, ads: 0 };
      const r = rewrite(bytes, 0, bytes.length, 0, stat);
      if (stat.items) console.log(`[YT HomeFeed] 首页卡片 ${stat.items} 张，删除广告 ${stat.ads} 张`);
      if (!r) return { bytes: body, changed: false };
      const out = new Uint8Array(r.len);
      let p = 0;
      for (const x of r.parts) {
        out.set(x, p);
        p += x.length;
      }
      return { bytes: out, changed: true };
    } catch (err) {
      console.log(`[YT HomeFeed] 出错，原样放行：${err}`);
      return { bytes: body, changed: false };
    }
  };
})();
