// 完整回归:覆盖无空格 @、参数映射、误触防护、指令
import http from "node:http"
import zlib from "node:zlib"
import { createRequire } from "node:module"
import { createHash } from "node:crypto"
const require = createRequire(import.meta.url)

const errors = []
const logger = {
  info: (...a) => { if (process.env.MEME_DEBUG) console.log("   [dbg]", ...a) },
  error: (...a) => errors.push("ERR " + a.join(" ")),
  warn: () => {}, mark: () => {}, debug: () => {}
}
globalThis.plugin = class { constructor(c) { this.cfg = c } }
globalThis.logger = logger
globalThis.segment = { image: (b) => ({ type: "image", buffer: b }) }
globalThis.Bot = { on: () => {} }

let TBL = null
function crc32(buf) {
  if (!TBL) { TBL = new Int32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; TBL[n] = c } }
  let c = 0xffffffff
  for (let i = 0; i < buf.length; i++) c = TBL[(c ^ buf[i]) & 0xff] ^ (c >>> 8)
  return c ^ 0xffffffff
}
function makePng(w = 220, h = 160) {
  const chunk = (t, d) => { const l = Buffer.alloc(4); l.writeUInt32BE(d.length); const td = Buffer.concat([Buffer.from(t), d]); const c = Buffer.alloc(4); c.writeUInt32BE(crc32(td) >>> 0); return Buffer.concat([l, td, c]) }
  const raw = Buffer.alloc((w * 3 + 1) * h)
  for (let y = 0; y < h; y++) { raw[y * (w * 3 + 1)] = 0; for (let x = 0; x < w; x++) { const o = y * (w * 3 + 1) + 1 + x * 3; raw[o] = 215; raw[o + 1] = 105; raw[o + 2] = 105 } }
  const ih = Buffer.alloc(13); ih.writeUInt32BE(w, 0); ih.writeUInt32BE(h, 4); ih[8] = 8; ih[9] = 2
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", ih), chunk("IDAT", zlib.deflateSync(raw)), chunk("IEND", Buffer.alloc(0))])
}
const PNG_BUF = makePng()
const srv = http.createServer((q, r) => { r.writeHead(200, { "Content-Type": "image/png", "Content-Length": PNG_BUF.length }); r.end(PNG_BUF) })
await new Promise((r) => srv.listen(8897, "127.0.0.1", r))
const AV = "http://127.0.0.1:8897/a.png"

const { MemePlugin } = await import("file:///D:/TRSSYUNZAI/Yunzai-Bot/plugins/meme-plugin/index.js")
const inst = new MemePlugin()

function ev(msg, o = {}) {
  const e = {
    msg, at: o.at || "", user_id: o.user_id || "1254803974",
    img: o.img || [], replies: [],
    async getReply() { return o.reply || null },
    group: {
      async pickMember(id) { return {
        async getInfo() { return { card: "鲁师傅", nickname: "鲁师傅", user_id: id } },
        async getAvatarUrl() { return AV } } },
      async getChatHistory() { return [] }
    },
    bot: { async pickFriend() { return null } },
    async reply(r) { e.replies.push(r); return r }
  }
  return e
}

const cases = [
  ["摸",                    "image", "1图 · 自己头像"],
  ["摸 圆",                 "image", "circle 选项"],
  ["摸@鲁师傅",             "image", "无空格 @（本次修复）"],
  ["摸 @鲁师傅",            "image", "空格 @"],
  ["摸@鲁师傅 圆",          "image", "无空格 @ + 参数"],
  ["摸@12345",              "image", "数字 QQ 号 @"],
  ["看扁 可恶",              "image", "文字参数(非 ratio)"],
  ["看扁 3",                "image", "ratio 数值"],
  ["看扁",                  "image", "默认文字"],
  ["一直",                  "image", "always 正常"],
  ["一直 循环",             "image", "mode=loop"],
  ["一直 套娃",             "image", "mode=circle"],
  ["5000兆 我去 洛天依",    "image", "纯文字 2 段"],
  ["5000兆",                "image", "纯文字 + 默认"],
  ["滚",                    "image", "roll"],
  ["爬 5",                  "image", "crawl number 数值"],
  // earth-k 独占表情 -> 走 Python 引擎(8767)
  ["撅",                    "image", "do (python 引擎)"],
  ["狠撅",                  "image", "狠撅=hendo 独立模板(60ms)"],
  ["龟龟撅",                "image", "turtle_jue (python)"],
  ["大撅",                  "image", "big_do (python)"],
  ["猛撅",                  "none",  "mengjue 待主人确认素材"],
  ["安安举牌 你好",          "image", "acacia_anan_holdsign (文字类)"],
  ["狠撅@222222",            "image", "狠撅+@"],
  ["狠狠撅",                "image", "hendo 第二关键词"],
  ["为什么艾特我",           "image", "petpet 独有模板"],
  ["阿尼亚",                 "image", "petpet 别名->rust 模板"],
  ["想什么",                 "image", "petpet 别名->rust 模板"],
  ["随便聊聊",              "none",  "不该触发"],
  ["我在摸鱼",              "none",  "关键词在中间"],
  ["摸鱼",                  "image", "摸鱼=slacking_off,上游既有行为"],
  ["摸鱼群",                "none",  "关键词后粘汉字仍不误触"],
]

let pass = 0, fail = 0
for (const [msg, expect, desc] of cases) {
  errors.length = 0
  const e = ev(msg)
  let r
  try { r = await inst.accept(e) }
  catch (err) { console.log(`FAIL  "${msg}" THREW ${err.message}`); fail++; continue }
  const got = e.replies.length === 0 ? "none"
    : e.replies[0]?.type === "image" ? "image" : "text"
  const ok = got === expect
  ok ? pass++ : fail++
  const info = got === "image" ? `${e.replies[0].buffer.length}B`
    : got === "text" ? `"${String(e.replies[0]).slice(0, 44).replace(/\n/g, " / ")}"` : ""
  console.log(`${ok ? "PASS" : "FAIL"}  ${String(msg).padEnd(22)} ${desc.padEnd(22)} -> ${got} ${info}`)
  for (const l of errors) console.log("       ", l)
}

console.log("\n=== 指令 ===")
for (const [cmd, fn, arg] of [["表情包状态","onStatus",null],["表情包搜索 摸","onSearch","摸"],["表情包列表","onList",null]]) {
  const e = ev(cmd)
  try { const r = await inst[fn](e, arg); console.log(`PASS  ${cmd.padEnd(16)} -> "${String(r).slice(0, 60).replace(/\n/g, " / ")}"`) }
  catch (err) { console.log(`FAIL  ${cmd} ${err.message}`); fail++ }
}

// ---- 参数是否真的改变了输出(hash 比对)----
console.log("\n=== 参数生效性(不同参数应产出不同图片) ===")
async function renderRaw(key, args) {
  const B = "----r" + Math.random().toString(36).slice(2)
  const chunks = []
  const field = (n, v) => chunks.push(Buffer.from(
    `--${B}\r\nContent-Disposition: form-data; name="${n}"\r\n\r\n${v}\r\n`, "utf8"))
  field("key", key)
  if (args) field("args", JSON.stringify(args))
  chunks.push(Buffer.from(
    `--${B}\r\nContent-Disposition: form-data; name="images"; filename="a.png"\r\nContent-Type: image/png\r\n\r\n`, "utf8"))
  chunks.push(PNG_BUF); chunks.push(Buffer.from("\r\n"))
  chunks.push(Buffer.from(`--${B}--\r\n`, "utf8"))
  const r = await fetch("http://127.0.0.1:8766/render", {
    method: "POST",
    headers: { "Content-Type": `multipart/form-data; boundary=${B}` },
    body: Buffer.concat(chunks)
  })
  const b = Buffer.from(await r.arrayBuffer())
  return createHash("md5").update(b).digest("hex").slice(0, 8) + `/${b.length}B`
}

for (const [key, a, b, label] of [
  ["always", {}, { mode: "loop" }, "always: no-arg vs mode=loop"],
  ["always", {}, { mode: "circle" }, "always: no-arg vs mode=circle"],
  ["petpet", {}, { circle: true }, "petpet: circle"],
  ["look_flat", {}, { ratio: 1.4 }, "look_flat: ratio"],
]) {
  const [h1, h2] = [await renderRaw(key, a), await renderRaw(key, b)]
  const distinct = h1 !== h2
  distinct ? pass++ : fail++
  console.log(`${distinct ? "PASS" : "FAIL"}  ${label.padEnd(34)} ${h1} vs ${h2}`)
}

// 狠撅(hendo)必须和撅(do)输出不同的图：同一个素材、更快的播放速度。
// 如果哪天又被合并成别名，这里会 FAIL。
{
  const md5 = (b) => createHash("md5").update(b).digest("hex")
  const grab = async (msg) => {
    const e = ev(msg); await inst.accept(e)
    const r = e.replies[0]
    if (e.replies.length === 0) return null
    return r?.type === "image" ? md5(r.buffer) : "text"
  }
  const a = await grab("撅")
  const b = await grab("狠撅")
  const distinct = a && b && a !== b
  distinct ? pass++ : fail++
  console.log(`${distinct ? "PASS" : "FAIL"}  hendo vs do 输出必须不同   do=${a} hendo=${b}`)
}

srv.close()
console.log(`\n=== ${pass} passed, ${fail} failed ===`)