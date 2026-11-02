"""给模块里「响应脚本要改写、却会被 anti-AD 拒绝」的域名加 DIRECT 放行规则。

开屏这类接口靠响应脚本把素材改成过期，App 才会刷新本地缓存；配置里的
RULE-SET,anti_ad,REJECT 会让请求直接失败，脚本永远不运行，App 一直用旧缓存。
模块规则优先于配置规则（真机 2026-11-02 验证），所以在模块自己的 [Rule] 里放行即可。

用法：pass_script_hosts.py <anti-AD clash.yaml> <报告文件> <模块文件...>
anti-AD 文件为空或解析失败时，沿用报告文件里上一次的结果，并以非零状态退出。
"""
import re
import sys

BEGIN = "# >>> 自动放行：响应脚本要改写、会被 anti-AD 拒绝的域名（scripts/pass_script_hosts.py 生成）"
END = "# <<< 自动放行"
TOO_GENERIC = 20  # 一条 pattern 匹配的 anti-AD 域名超过这个数，视为通配，只警告不放行
PROBES = ("example.com", "a.example.org")  # 能匹配这些无关域名的 pattern 也视为通配

antiad_path, report_path, modules = sys.argv[1], sys.argv[2], sys.argv[3:]


def load_antiad(path):
    blocked = set()
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"\s*-\s*'\+\.([^']+)'", line)
                if m:
                    blocked.add(m.group(1).lower())
    except OSError:
        pass
    return blocked if len(blocked) > 10000 else None


def is_blocked(host, blocked):
    # anti-AD 的条目都是 +.域名，即本身及所有子域名
    parts = host.split(".")
    return any(".".join(parts[i:]) in blocked for i in range(len(parts)))


def host_regex(pattern):
    """取出 URL 正则里的域名部分；无法识别时返回 None。"""
    m = re.match(r"\^?(https?)\??:(\\/|/)(\\/|/)", pattern)
    if not m:
        return None, None
    out, depth, i = [], 0, m.end()
    while i < len(pattern):
        c = pattern[i]
        if c == "\\" and i + 1 < len(pattern):
            if pattern[i + 1] == "/" and depth == 0:
                break
            out.append(pattern[i:i + 2])
            i += 2
            continue
        if depth == 0 and c in "/:":
            break
        if c == "(":
            if depth == 0 and (pattern[i + 1:i + 2] == "/" or pattern[i + 1:i + 3] == "\\/"):
                break
            depth += 1
        elif c == ")":
            depth -= 1
        out.append(c)
        i += 1
    return m.group(1), "".join(out)


class NotFinite(Exception):
    pass


def expand(hr, limit=64):
    """把只含字面量、分组、| 和 ? 的域名正则展开成具体域名；含 * + {} [] \\d 等时返回 None。
    域名语境里单独的 . 按字面的点处理（规则作者常写 new.vip.weibo.cn 而不转义）。"""
    def alts(i):
        out = []
        while True:
            seq, i = sequence(i)
            out += seq
            if i < len(hr) and hr[i] == "|":
                i += 1
                continue
            return out, i

    def sequence(i):
        cur = [""]
        while i < len(hr) and hr[i] not in "|)":
            c = hr[i]
            if c == "\\":
                if hr[i + 1:i + 2] not in (".", "-"):
                    raise NotFinite
                atom, i = [hr[i + 1]], i + 2
            elif c == "(":
                j = i + 3 if hr.startswith("(?:", i) else i + 1
                atom, i = alts(j)
                if i >= len(hr) or hr[i] != ")":
                    raise NotFinite
                i += 1
            elif c.isalnum() or c in ".-_":
                atom, i = [c], i + 1
            else:
                raise NotFinite
            if i < len(hr) and hr[i] in "*+{":
                raise NotFinite
            if i < len(hr) and hr[i] == "?":
                atom, i = atom + [""], i + 1
            cur = [a + b for a in cur for b in atom]
            if len(cur) > limit:
                raise NotFinite
        return cur, i

    try:
        hosts, i = alts(0)
    except (NotFinite, IndexError):
        return None
    return [h.lower() for h in hosts] if i == len(hr) else None


def is_generic(hr):
    try:
        return any(re.fullmatch(hr, p, re.I) for p in PROBES)
    except re.error:
        return True


def parse(lines):
    """返回 (响应改写的 pattern 列表, MITM 主机列表, 模块里有显式 DOMAIN 规则的域名, REJECT 规则)"""
    section, patterns, mitm, explicit, rejects = None, [], [], set(), []
    for raw in lines:
        line = raw.strip()
        if re.fullmatch(r"\[.+\]", line):
            section = line[1:-1]
        elif section == "Rule" and not line.startswith("#"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3 and parts[0] == "DOMAIN":
                explicit.add(parts[1].lower())
            if len(parts) >= 3 and parts[0] in ("DOMAIN", "DOMAIN-SUFFIX") and parts[2] == "REJECT":
                rejects.append((parts[0], parts[1].lower()))
        elif section == "Script" and "type=http-response" in line:
            m = re.search(r'pattern=("([^"]*)"|[^,]+)', line)
            if m:
                patterns.append(m.group(2) if m.group(2) is not None else m.group(1))
        elif section == "Body Rewrite" and line.startswith("http-response"):
            patterns.append(line.split()[1])
        elif section == "MITM" and line.startswith("hostname"):
            value = line.split("=", 1)[1].replace("%APPEND%", "")
            mitm += [h.strip().lower() for h in value.split(",") if h.strip()]
    return patterns, mitm, explicit, rejects


def strip_block(lines):
    out, skipping = [], False
    for line in lines:
        if line.rstrip("\n") == BEGIN:
            skipping = True
        elif skipping and line.rstrip("\n") == END:
            skipping = False
        elif not skipping:
            out.append(line)
    return out


def insert_block(lines, hosts):
    if not hosts:
        return lines
    block = [BEGIN + "\n"] + [f"DOMAIN,{h},DIRECT\n" for h in hosts] + [END + "\n"]
    for i, line in enumerate(lines):
        if line.strip() == "[Rule]":
            return lines[:i + 1] + block + lines[i + 1:]
    # 没有 [Rule] 段：放在开头的 #! 元信息之后
    i = 0
    while i < len(lines) and (lines[i].startswith("#!") or not lines[i].strip()):
        i += 1
    return lines[:i] + ["[Rule]\n"] + block + ["\n"] + lines[i:]


def compute(name, patterns, mitm, explicit, blocked):
    literal_mitm = [h for h in mitm if "*" not in h]
    mitm_rx = [re.compile(re.escape(h).replace(r"\*", ".*")) for h in mitm]
    found = {}
    for pattern in patterns:
        scheme, hr = host_regex(pattern)
        if hr is None:
            print(f"  警告 {name}: 无法识别域名部分，跳过 {pattern}")
            continue
        try:
            rx = re.compile(hr, re.I)
        except re.error:
            print(f"  警告 {name}: 域名部分不是合法正则，跳过 {hr}")
            continue
        concrete = expand(hr)
        if concrete is not None:
            # 能展开成具体域名：逐个按后缀判断，能发现只被上级域名（如 +.biz.weibo.com）拦住的接口
            hits = [h for h in concrete if is_blocked(h, blocked)]
        elif is_generic(hr):
            print(f"  提示 {name}: {hr} 是通配域名，不参与放行")
            continue
        else:
            hits = [d for d in blocked if rx.fullmatch(d)]
            if len(hits) > TOO_GENERIC:
                print(f"  警告 {name}: {hr} 匹配 {len(hits)} 个 anti-AD 域名，视为通配，不放行")
                continue
            hits += [h for h in literal_mitm if rx.fullmatch(h) and is_blocked(h, blocked)]
        for host in hits:
            # https 接口不在 MITM 范围内时脚本本来就不会运行，放行没有意义
            if scheme == "https" and not any(m.fullmatch(host) for m in mitm_rx):
                continue
            if host in explicit:
                continue
            found.setdefault(host, hr)
    return found


blocked = load_antiad(antiad_path)
previous = {}
try:
    with open(report_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            module, host, hr = line.rstrip("\n").split("\t", 2)
            previous.setdefault(module, {})[host] = hr
except OSError:
    pass
if blocked is None:
    print(f"  警告 anti-AD 列表不可用，沿用上一次的放行结果（{sum(map(len, previous.values()))} 条）")

report, parsed = [], {}
for path in modules:
    name = path.rsplit("/", 1)[-1]
    with open(path, encoding="utf-8") as f:
        lines = strip_block(f.readlines())
    patterns, mitm, explicit, rejects = parse(lines)
    parsed[name] = (patterns, rejects)
    if blocked is None:
        hosts = previous.get(name, {})
    else:
        hosts = compute(name, patterns, mitm, explicit, blocked)
    for host, hr in sorted(hosts.items()):
        report.append(f"{name}\t{host}\t{hr}")
        print(f"  放行 {name}: {host}  ← {hr}")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(insert_block(lines, sorted(hosts)))

# 跨模块冲突：一个模块 REJECT 了另一个模块脚本要改写的域名，模块之间谁优先没有验证过，只提示
for name, (_, rejects) in parsed.items():
    for kind, domain in rejects:
        for other, (patterns, _) in parsed.items():
            for pattern in patterns:
                _, hr = host_regex(pattern)
                if hr and other != name and not is_generic(hr) and re.fullmatch(hr, domain, re.I):
                    print(f"  警告 {name} 的 {kind},{domain},REJECT 会拦掉 {other} 的响应脚本 {hr}")

with open(report_path, "w", encoding="utf-8") as f:
    f.write("# 模块\t放行的域名\t对应的响应改写 pattern（域名部分）\n")
    f.writelines(line + "\n" for line in report)

sys.exit(0 if blocked is not None else 1)
