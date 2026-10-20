/**
 * 自建表情包插件 (meme-plugin)
 * ----------------------------
 * 触发协议对齐 earth-k-plugin 的「土块表情」:
 *
 *   <关键词>                  → 艾特的人 / 自己 / 回复消息里的图
 *   <关键词>@某人             → 某人的头像（不带空格也支持）
 *   <关键词> @某人            → 同上
 *   <关键词> 文字1 文字2      → 多个文字参数
 *   <关键词> 圆 / 左 / 右 ...  → 可选参数
 *
 * 渲染全部在本机 D:\TRSSYUNZAI\MemeService 完成,
 * 图片/字体素材已本地化,不依赖任何外部接口。
 */
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const PLUGIN_NAME = "自建表情包"
const SERVICE = "http://127.0.0.1:8766"          // Rust 引擎 (meme-generator-rs)
const LEGACY_SERVICE = "http://127.0.0.1:8767"  // Python 引擎 (earth-k 独占的那批表情)

/** 开关状态:0=关闭 1=开启 */
let kg = 1

/** 关键词 -> 表情元数据(启动时从本地词表加载) */
const bq = {}

/** 关键词匹配用的正则(最长优先,避免 "摸" 抢走 "摸摸头") */
let reg = null

/** 表情 key -> 真实支持的 options(含类型),用于校验参数名 */
const memeOptions = new Map()

/** 表情 key -> { min, max },用于判断第一个 token 是参数还是文字 */
const memeTexts = new Map()

/** 表情 key -> 单段文字的最大字数(上游部分表情会声明比 max_texts 更长的默认值) */
const memeMaxLen = new Map()

/** 表情 key -> "rust" | "python",决定请求打向哪个渲染服务 */
const memeEngine = new Map()

/** 默认文字表(服务端 /memes 提供) */
const defaultTexts = new Map()

/**
 * 可选参数的中文别名表 —— 按 option 名称组织,而不是按表情 key。
 * 这样新增表情时只要它用了这些 option 名就自动支持。
 * 值的类型(bool/number/string)与服务端 /memes 声明一致。
 */
const ARG_ALIAS = {
  // 圆形头像/圆形裁切
  circle: { 圆: true, 方: false },
  // always: normal / loop / circle
  mode: { "": "normal", 正常: "normal", 循环: "loop", 套娃: "circle" },
  loop: { 循环: true },
  // look_flat 压扁比例
  ratio: { __num: true },
  // crawl / *_holdsign 编号
  number: { __num: true },
  size: { __num: true },
  rotate: { __num: true },
  x_offset: { __num: true },
  y_offset: { __num: true },
  stroke_width: { __num: true },
  // 方向类(布尔形式,服务端实际支持的)
  left: { 左: true },
  right: { 右: true },
  top: { 上: true },
  bottom: { 下: true },
  both: { 两边: true, 两侧: true },
  left_right: { 左右: true },
  right_left: { 右左: true },
  // 位置类
  position: { 左: "left", 右: "right", 两边: "both", 上: "top", 下: "bottom" },
  direction: { 左: "left", 右: "right", 上: "top", 下: "bottom" },
  // 性别
  gender: { 男: "male", 女: "female", 他: "male", 她: "female" },
  // 人称
  pronoun: { 他: "his", 她: "her", 我: "my", 你: "your" },
  // 文字内容类
  name: { __text: true },
  message: { __text: true },
  character: { __text: true },
  font: { __text: true },
  color: { __text: true },
  align: { 左: "left", 右: "right", 居中: "center", 居中对齐: "center" },
  // misc 开关
  gray: { 灰: true, 黑白: true },
  bold: { 粗: true, 加粗: true },
  italic: { 斜: true, 斜体: true },
  mirror: { 翻转: true, 镜像: true },
  front: { 前: true },
  behind: { 后: true },
  block_text: { 方块: true, 方块字: true },
  yes: { 是: true, 对: true },
  no: { 否: true, 不: true },
  person: { 人: true, 人物: true }
}

/** loadlook 的镜像是 mirror:true(与 ARG_ALIAS 一致) */

/** 按表情声明的单段字数上限截断文字(服务端超长会直接拒绝) */
function clampText(text, key) {
  const limit = memeMaxLen.get(key)
  if (!limit || !text) return text
  // 按 Unicode 码点切,避免把 emoji / 生僻字劈成半个
  const arr = Array.from(text)
  return arr.length > limit ? arr.slice(0, limit).join("") : text
}

/** 把单个中文 token 翻译成 args 对象 */
function buildArgs(key, rawArg, userInfos) {
  const arg = (rawArg || "").trim()
  const args = {}
  if (!arg) return args

  // 该表情支持哪些 option
  const supported = memeOptions.get(key)

  // --- 1) 文本类 option(整段当值) ---
  // name: 直接把内容当名字(仅当表情支持 name)
  if (supports(supported, "name") && ARG_ALIAS.name?.__text) {
    args.name = arg
    return args
  }
  if (supports(supported, "message") && ARG_ALIAS.message?.__text) {
    args.message = arg
    return args
  }
  if (supports(supported, "character") && ARG_ALIAS.character?.__text) {
    args.character = arg
    return args
  }

  // --- 2) 数字类 option ---
  for (const name of ["ratio", "number", "size", "rotate"]) {
    if (!supports(supported, name)) continue
    const n = Number(arg)
    if (Number.isFinite(n)) {
      args[name] = n
      return args
    }
  }

  // --- 3) mode 字符串 ---
  if (supports(supported, "mode")) {
    const v = ARG_ALIAS.mode[arg]
    if (v !== undefined) {
      args.mode = v
      return args
    }
  }

  // --- 4) 枚举字符串(position / direction / gender / pronoun / align) ---
  for (const name of ["position", "direction", "gender", "pronoun", "align"]) {
    if (!supports(supported, name)) continue
    const v = ARG_ALIAS[name]?.[arg]
    if (v !== undefined) {
      args[name] = v
      return args
    }
  }

  // --- 5) 布尔量(方向类/开关类) ---
  for (const [name, table] of Object.entries(ARG_ALIAS)) {
    if (!supports(supported, name)) continue
    if (typeof table !== "object" || table.__num || table.__text) continue
    const v = table[arg]
    if (v !== undefined) {
      args[name] = v
      return args
    }
  }

  return args
}

/** 表情是否支持该 option(没拿到元数据时保守返回 false) */
function supports(supported, name) {
  if (!supported) return false
  return supported.has(name)
}

/** 组装 multipart/form-data(可带多个 images) */
async function renderService({ key, engine = "rust", images = [], texts = [], args = null }) {
  const boundary =
    "----memeplugin" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
  const chunks = []

  const field = (name, value) => {
    chunks.push(
      Buffer.from(
        `--${boundary}\r\nContent-Disposition: form-data; name="${name}"\r\n\r\n${value}\r\n`,
        "utf8"
      )
    )
  }

  field("key", key)
  for (const t of texts) field("texts", t)
  if (args && Object.keys(args).length) field("args", JSON.stringify(args))

  for (let i = 0; i < images.length; i++) {
    const buf = images[i]
    if (!buf) continue
    chunks.push(
      Buffer.from(
        `--${boundary}\r\nContent-Disposition: form-data; name="images"; filename="user_${i}.png"\r\n` +
          `Content-Type: image/png\r\n\r\n`,
        "utf8"
      )
    )
    chunks.push(buf)
    chunks.push(Buffer.from("\r\n", "utf8"))
  }

  chunks.push(Buffer.from(`--${boundary}--\r\n`, "utf8"))

  const base = engine === "python" ? LEGACY_SERVICE : SERVICE
  const resp = await fetch(`${base}/render`, {
    method: "POST",
    headers: { "Content-Type": `multipart/form-data; boundary=${boundary}` },
    body: Buffer.concat(chunks)
  })

  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`
    try {
      const j = await resp.json()
      if (j && j.error) msg = j.error
    } catch { /* 保持默认文案 */ }
    throw new Error(msg)
  }

  return Buffer.from(await resp.arrayBuffer())
}

/** 下载头像/图片并转成 buffer */
async function fetchImage(url) {
  if (!url) return null
  try {
    const resp = await fetch(url, { timeout: 15000 })
    if (!resp.ok) return null
    const buf = Buffer.from(await resp.arrayBuffer())
    return buf.length > 0 ? buf : null
  } catch {
    return null
  }
}

export class MemePlugin extends plugin {
  constructor() {
    super({
      name: PLUGIN_NAME,
      dsc: "本地渲染的表情包,不依赖第三方接口",
      event: "message",
      priority: 1146,
      rule: [
        { reg: "^#?表情包开启$", fnc: "onEnable" },
        { reg: "^#?表情包关闭$", fnc: "onDisable" },
        { reg: "^#?表情包状态$", fnc: "onStatus" },
        { reg: "^#?表情包列表$", fnc: "onList" },
        { reg: "^#?表情包搜索\\s*(.+)$", fnc: "onSearch" }
      ]
    })
    this.loadKeywordTable()
    this.loadMemeMeta()
  }

  /** 加载本地关键词表 */
  loadKeywordTable() {
    try {
      const file = path.join(__dirname, "resources", "memes.json")
      const raw = JSON.parse(fs.readFileSync(file, "utf8"))
      for (const item of raw) {
        if (item.engine) memeEngine.set(item.key, item.engine)
        for (const kw of item.keywords || []) {
          if (!bq[kw]) bq[kw] = item
        }
      }
      const keys = Object.keys(bq).sort((a, b) => b.length - a.length)
      reg = new RegExp(`^(${keys.map(escapeRegExp).join("|")})`)
      logger.info(`[${PLUGIN_NAME}] 已加载 ${raw.length} 个表情 / ${keys.length} 个关键词`)
    } catch (err) {
      logger.error(`[${PLUGIN_NAME}] 关键词表加载失败: ${err.message}`)
    }
  }

  /** 从本地词表补齐 option / 文字约束元数据 */
  loadMemeMeta() {
    try {
      const file = path.join(__dirname, "resources", "memes.json")
      const raw = JSON.parse(fs.readFileSync(file, "utf8"))
      for (const item of raw) {
        if (item.engine) memeEngine.set(item.key, item.engine)
        if (Array.isArray(item.options) && item.options.length) {
          memeOptions.set(item.key, new Set(item.options))
        }
        memeTexts.set(item.key, {
          min: item.min_texts ?? 0,
          max: item.max_texts ?? 0
        })
        if (item.text_max_length) memeMaxLen.set(item.key, item.text_max_length)
        if (Array.isArray(item.default_texts) && item.default_texts.length) {
          defaultTexts.set(item.key, item.default_texts)
        }
      }
    } catch (err) {
      logger.error(`[${PLUGIN_NAME}] 表情元数据加载失败: ${err.message}`)
    }
  }

  onEnable(e) {
    kg = 1
    return e.reply("表情功能已开启")
  }

  onDisable(e) {
    kg = 0
    return e.reply("表情功能已关闭")
  }

  async onStatus(e) {
    const total = new Set(Object.values(bq).map((i) => i.key)).size
    const parts = []
    for (const [label, base] of [["Rust", SERVICE], ["Python", LEGACY_SERVICE]]) {
      try {
        const r = await fetch(`${base}/health`, { timeout: 5000 })
        const j = await r.json()
        parts.push(`${label} ${j.memes} 个${j.images_on_disk ? ` / ${j.images_on_disk} 张素材` : ""}`)
      } catch {
        parts.push(`${label} 不可用`)
      }
    }
    const svc = parts.join("\n")
    return e.reply(
      `表情功能：${kg ? "已开启" : "已关闭"}\n` +
        `本地表情：${total} 个 / 关键词 ${Object.keys(bq).length} 个\n` +
        `渲染服务：${svc}`
    )
  }

  async onList(e) {
    const keys = [...new Set(Object.values(bq).map((i) => i.key))].sort()
    return e.reply(
      `共 ${keys.length} 个表情，发送「表情包搜索 关键词」查看用法\n\n` + keys.join("  ")
    )
  }

  async onSearch(e, keyword) {
    const kw = (keyword || "").trim()
    const item = bq[kw]
    if (!item) {
      const found = [
        ...new Set(
          Object.values(bq).filter(
            (i) => i.key.includes(kw) || (i.keywords || []).some((k) => k.includes(kw))
          )
        )
      ]
      if (!found.length) return e.reply(`没有找到和「${kw}」相关的表情`)
      return e.reply(
        found
          .slice(0, 20)
          .map((i) => `${(i.keywords || []).join("/")}  →  ${i.key}`)
          .join("\n")
      )
    }
    const need = []
    if (item.min_images > 0) need.push(`${item.min_images}~${item.max_images} 张图`)
    if (item.min_texts > 0) need.push(`${item.min_texts}~${item.max_texts} 段文字`)
    const opts = (item.options || []).length ? `\n可选参数：${item.options.join(" ")}` : ""
    return e.reply(
      `表情：${(item.keywords || []).join(" / ")}\n` +
        `key: ${item.key}\n` +
        `需要：${need.length ? need.join("，") : "什么都不用，直接发就行"}` +
        opts
    )
  }

  async accept(e) {
    if (kg === 0) return
    const msg = e.msg
    if (!msg || !reg) return

    const match = msg.match(reg)?.[0]
    if (!match) return

    const item = bq[match]
    if (!item) return

    // ---- 拆词:关键词后面的部分 ----
    // 支持「摸」「摸@某人」「摸 @某人」「摸文字」「摸@某人 文字」四种写法
    let rest = msg.slice(match.length).trim()

    // 紧跟在关键词后面的 @某人(不带空格)
    let atFromToken = null
    const atHead = rest.match(/^@([^\s]+)/)
    if (atHead) {
      atFromToken = atHead[1]
      rest = rest.slice(atHead[0].length)
    }

    // 剩下的按空格切
    let tokens = rest.split(/\s+/).filter((t) => t !== "")

    // token 内部的 @某人(例如 "文字@12345" 少见,但 "我@你" 之类要能取到)
    let extraAt = null
    for (let i = 0; i < tokens.length; i++) {
      const m = tokens[i].match(/@([^\s]+)/)
      if (m) {
        extraAt = m[1]
        tokens[i] = tokens[i].replace(/@([^\s]+)/, "")
        if (tokens[i] === "") tokens.splice(i, 1)
        break
      }
    }

    // ---- 守卫:关键词后面粘着别的字说明是正常聊天(「摸鱼」「摸黑」不该触发)----
    // earth-k 用的是 `/^[\u0000-~]+$/`:只允许 ASCII 紧跟在关键词后
    // (即 @某人 / 英文 / 数字),其余一律视为误触。
    const after = msg.slice(match.length)
    if (after && !/^[\u0000-\u007f]/.test(after[0])) {
      const hasAt = /^@\S/.test(after)
      const isAsciiRun = /^[\u0000-\u007f]+/.test(after)
      if (!hasAt && !isAsciiRun) return
    }

    const need = item.min_images || 0
    const textSpec = memeTexts.get(item.key) || { min: 0, max: 0 }

    // ---- 取被艾特的人的头像 ----
    const atId = atFromToken || extraAt || e.at || e.user_id
    const pick = await this.pickUser(e, atId)
    const userName = pick?.name || ""

    // ---- 组装图片 ----
    const images = []

    // 1) 回复消息里的图优先
    const replied = await this.getRepliedImage(e)
    if (replied) images.push(replied)

    // 2) 自己发的图
    if (images.length < need && e.img?.[0]) {
      const buf = await fetchImage(e.img[0])
      if (buf) images.push(buf)
    }

    // 3) 被艾特的人的头像(earth-k 同款 qlogo 兜底)
    while (images.length < need) {
      const url =
        (await this.getAvatarUrl(e, pick, atId)) ||
        `http://q2.qlogo.cn/headimg_dl?dst_uin=${atId}&spec=5`
      const buf = await fetchImage(url)
      if (buf) {
        images.push(buf)
        continue
      }
      break
    }

    if (images.length < need) {
      return e.reply(
        `「${match}」需要 ${need} 张图片。\n` +
          `发图、回复一条带图的消息、或艾特一个人(取他头像)都可以。`,
        true
      )
    }

    // ---- 组装文字与参数 ----
    //
    // 歧义处理:31 个表情声明 min_texts=0 且 max_texts=1,
    // 也就是第一个 token 到底是「参数」还是「文字」两说。
    // 规则:只有该表情真的声明了 option 时,首个 token 才可能是参数;
    // 没有 option 的表情(min=0,max=1 但无参数)首个 token 一律当文字。
    let texts = tokens.slice()
    let rawArg = ""
    const hasOptions = (memeOptions.get(item.key)?.size ?? 0) > 0

    if (hasOptions && textSpec.min === 0 && texts.length > 0) {
      rawArg = texts[0]
      texts = texts.slice(1)
    } else if (textSpec.max === 0 && texts.length > 0) {
      // 既无文字也无参数(193 个纯参数表情):不该有剩余 token
      texts = []
    }

    // 文字表情缺文字时补默认文字
    if (texts.length === 0) {
      const d = defaultTexts.get(item.key)
      if (d?.length) {
        const cap = textSpec.max > 0 ? textSpec.max : d.length
        texts = d.slice(0, Math.min(d.length, cap))
      }
    }

    // 用户输入的文字可能超长,服务端会直接拒。
    // 只在该表情声明了字数上限时截断;没声明就不猜。
    texts = texts.map((t) => clampText(t, item.key))

    const args = buildArgs(item.key, rawArg, [{ text: userName, gender: "unknown" }])

    if (process.env.MEME_DEBUG) {
      logger.info(
        `[${PLUGIN_NAME}] ${item.key} texts=${JSON.stringify(texts)} ` +
          `engine=${memeEngine.get(item.key)} images=${images.length} args=${JSON.stringify(args)}`
      )
    }

    try {
      const buf = await renderService({
        key: item.key,
        engine: memeEngine.get(item.key) || "rust",
        images,
        texts,
        args: Object.keys(args).length ? args : null
      })
      return e.reply(segment.image(buf))
    } catch (err) {
      logger.error(`[${PLUGIN_NAME}] 渲染 ${item.key} 失败: ${err.message}`)
      return e.reply(`表情生成失败：${err.message}`, true)
    }
  }

  /** 取用户昵称/群名片 */
  async pickUser(e, id) {
    try {
      const pick =
        (await e.group?.pickMember?.(id)) || (await e.bot?.pickFriend?.(id))
      if (!pick) return null
      const info = (await pick.getInfo?.()) || pick.info || pick
      return { name: info?.card || info?.nickname || "", raw: pick, info }
    } catch {
      return null
    }
  }

  /** 取头像 URL(QQ 号走 qlogo,避免 pick 对象在私聊/群聊不一致时拿到空) */
  async getAvatarUrl(e, pick, id) {
    try {
      const url = await pick?.raw?.getAvatarUrl?.()
      if (url) return url
    } catch { /* 退回 qlogo */ }
    return null
  }

  /** 取被回复消息里的第一张图 */
  async getRepliedImage(e) {
    try {
      let reply = null
      if (e.getReply) {
        reply = await e.getReply()
      } else if (e.source) {
        if (e.group?.getChatHistory) {
          reply = (await e.group.getChatHistory(e.source.seq, 1)).pop()
        } else if (e.friend?.getChatHistory) {
          reply = (await e.friend.getChatHistory(e.source.time, 1)).pop()
        }
      }
      if (!reply?.message) return null
      for (const seg of reply.message) {
        if ((seg.type === "image" || seg.type === "file") && seg.url) {
          return fetchImage(seg.url)
        }
      }
    } catch { /* 拿不到就算了 */ }
    return null
  }
}

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}