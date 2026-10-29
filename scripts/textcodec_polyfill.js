// TextDecoder / TextEncoder 最小实现（仅 UTF-8），给没有 Web API 的脚本引擎用。
// 宿主已有原生实现时不做任何事。
;(function (g) {
  if (typeof g.TextDecoder === 'function' && typeof g.TextEncoder === 'function') return

  function toBytes(input) {
    if (input == null) return new Uint8Array(0)
    if (input instanceof Uint8Array) return input
    if (input instanceof ArrayBuffer) return new Uint8Array(input)
    if (ArrayBuffer.isView(input)) return new Uint8Array(input.buffer, input.byteOffset, input.byteLength)
    throw new TypeError("Failed to execute 'decode' on 'TextDecoder': unsupported input")
  }

  function TextDecoder(label, options) {
    var enc = String(label === undefined ? 'utf-8' : label).toLowerCase()
    if (enc !== 'utf-8' && enc !== 'utf8' && enc !== 'unicode-1-1-utf-8') throw new RangeError('TextDecoder polyfill only supports utf-8, got ' + label)
    this.encoding = 'utf-8'
    this.fatal = !!(options && options.fatal)
    this.ignoreBOM = !!(options && options.ignoreBOM)
    this._reset()
    this._bomSeen = false
  }
  TextDecoder.prototype._reset = function () {
    this._cp = 0; this._needed = 0; this._seen = 0; this._lower = 0x80; this._upper = 0xbf
  }
  // WHATWG Encoding 规范的 UTF-8 解码状态机：残缺序列整体替换为一个 U+FFFD
  TextDecoder.prototype.decode = function (input, options) {
    var bytes = toBytes(input)
    var stream = !!(options && options.stream)
    var out = []
    var chunk = ''
    var self = this
    function emit(cp) {
      if (!self._bomSeen) {
        self._bomSeen = true
        if (cp === 0xfeff && !self.ignoreBOM) return
      }
      if (cp > 0xffff) {
        cp -= 0x10000
        chunk += String.fromCharCode(0xd800 + (cp >> 10), 0xdc00 + (cp & 0x3ff))
      } else chunk += String.fromCharCode(cp)
      if (chunk.length > 8192) { out.push(chunk); chunk = '' }
    }
    function error() {
      if (self.fatal) { self._reset(); throw new TypeError('The encoded data was not valid utf-8') }
      emit(0xfffd)
    }
    for (var i = 0; i < bytes.length; i++) {
      var b = bytes[i]
      if (this._needed === 0) {
        if (b <= 0x7f) emit(b)
        else if (b >= 0xc2 && b <= 0xdf) { this._needed = 1; this._cp = b & 0x1f }
        else if (b >= 0xe0 && b <= 0xef) {
          if (b === 0xe0) this._lower = 0xa0
          if (b === 0xed) this._upper = 0x9f
          this._needed = 2; this._cp = b & 0x0f
        } else if (b >= 0xf0 && b <= 0xf4) {
          if (b === 0xf0) this._lower = 0x90
          if (b === 0xf4) this._upper = 0x8f
          this._needed = 3; this._cp = b & 0x07
        } else error()
        continue
      }
      if (b < this._lower || b > this._upper) {
        this._reset()
        error()
        i--  // 规范要求：出错的字节重新按首字节处理
        continue
      }
      this._lower = 0x80; this._upper = 0xbf
      this._cp = (this._cp << 6) | (b & 0x3f)
      if (++this._seen === this._needed) {
        var cp = this._cp
        this._reset()
        emit(cp)
      }
    }
    if (!stream) {
      if (this._needed !== 0) { this._reset(); error() }
      this._bomSeen = false
    }
    out.push(chunk)
    return out.join('')
  }

  function TextEncoder() { this.encoding = 'utf-8' }
  TextEncoder.prototype.encode = function (str) {
    str = str === undefined ? '' : String(str)
    var buf = new Uint8Array(str.length * 3)
    var p = 0
    for (var i = 0; i < str.length; i++) {
      var c = str.charCodeAt(i)
      if (c >= 0xd800 && c <= 0xdbff && i + 1 < str.length) {
        var d = str.charCodeAt(i + 1)
        if (d >= 0xdc00 && d <= 0xdfff) { c = 0x10000 + ((c - 0xd800) << 10) + (d - 0xdc00); i++ } else c = 0xfffd
      } else if (c >= 0xd800 && c <= 0xdfff) c = 0xfffd
      if (c < 0x80) buf[p++] = c
      else if (c < 0x800) { buf[p++] = 0xc0 | (c >> 6); buf[p++] = 0x80 | (c & 0x3f) }
      else if (c < 0x10000) { buf[p++] = 0xe0 | (c >> 12); buf[p++] = 0x80 | ((c >> 6) & 0x3f); buf[p++] = 0x80 | (c & 0x3f) }
      else { buf[p++] = 0xf0 | (c >> 18); buf[p++] = 0x80 | ((c >> 12) & 0x3f); buf[p++] = 0x80 | ((c >> 6) & 0x3f); buf[p++] = 0x80 | (c & 0x3f) }
    }
    return buf.slice(0, p)
  }
  TextEncoder.prototype.encodeInto = function (str, dest) {
    var b = this.encode(str)
    var w = Math.min(b.length, dest.length)
    dest.set(b.subarray(0, w))
    return { read: str.length, written: w }
  }

  if (typeof g.TextDecoder !== 'function') g.TextDecoder = TextDecoder
  if (typeof g.TextEncoder !== 'function') g.TextEncoder = TextEncoder
})(typeof globalThis !== 'undefined' ? globalThis : this)
