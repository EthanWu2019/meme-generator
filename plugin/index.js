/**
 * 自建表情包插件 (meme-plugin)
 * ----------------------------
 * 触发协议与 earth-k-plugin 的「土块表情」完全一致,可以直接平替:
 *
 *   <关键词>                    → 用艾特的人/自己的头像 + 后续文字
 *   <关键词>@某人               → 用某人的头像
 *   <关键词> @某人              → 同上
 *   <关键词> 文字1 文字2        → 多个文字参数(空格分隔)
 *   <关键词> 圆 / 翻转 / 左 ...   → 特殊参数
 *
 * 不需要艾特的(纯文字表情,min_images=0):直接发 <关键词> 文字1 文字2
 *
 * 渲染全部在本机 D:\TRSSYUNZAI\MemeService 完成,
 * 图片/字体资源已本地化,不依赖任何外部接口。
 */
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const PLUGIN_NAME = "自建表情包"
const SERVICE = "http://127.0.0.1:8766"

/** 开关状态:0=关闭 1=开启 */
let kg = 1

/** 关键词 -> 表情元数据(启动时从本地词表加载) */
const bq = {}

/** 关键词匹配用的正则(最长优先,避免 "摸" 抢走 "摸摸头") */
let reg = null

/** 用户名注入用:和 earth-k 保持一致 */
function parseUserInfos(text, gender = "unknown") {
  return [{ text: (text || "").replace(/^@/, "").trim(), gender }]
}

/** 特殊参数:把中文参数翻译成 meme_generator 的 options */
function buildArgs(key, rawArg, userInfos) {
  const arg = (rawArg || "").trim()
  const args = {}

  switch (key) {
    case "look_flat":
      args.ratio = parseInt(arg, 10) || 2
      break
    case "crawl":
      args.number = parseInt(arg, 10) || 1
      break
    case "symmetric": {
      const map = { 左: "left", 右: "right", 上: "top", 下: "bottom" }
      args.direction = map[arg] || "left"
      break
    }
    case "petpet":
    case "jiji_king":
    case "kirby_hammer":
      args.circle = arg.startsWith("圆")
      break
    case "my_friend":
      args.name = arg || userInfos[0].text
      break
    case "looklook":
      args.mirror = arg === "翻转"
      break
    case "always": {
      const map = { "": "normal", 循环: "loop", 套娃: "circle" }
      args.mode = map[arg] || "normal"
      break
    }
    case "gun":
    case "bubble_tea": {
      const map = { 左: "left", 右: "right", 两边: "both" }
      args.position = map[arg] || "right"
      break
    }
  }
  return args
}

/** 组装 multipart/form-data */
function buildForm({ key, texts, args }) {
  const boundary = "----memeplugin" + Date.now().toString(36)
  const chunks = []
  const push = (name, value) => {
    chunks.push(
      Buffer.from(
        `--${boundary}\r\nContent-Disposition: form-data; name="${name}"\r\n\r\n${value}\r\n`,
        "utf8"
      )
    )
  }
  push("key", key)
  for (const t of texts) push("texts", t)
  if (args && Object.keys(args).length) push("args", JSON.stringify(args))
  chunks.push(Buffer.from(`--${boundary}--\r\n`, "utf8"))
  return { body: Buffer.concat(chunks), contentType: `multipart/form-data; boundary=${boundary}` }
}

/** 调用本地渲染服务 */
async function renderService({ key, images = [], texts = [], args = null }) {
  const boundary = "----memeplugin" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
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

  const resp = await fetch(`${SERVICE}/render`, {
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

/** 下载头像并转成 buffer */
async function fetchAvatar(url) {
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
      dsc: "本地渲染的表情包,不需要联网调用第三方接口",
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
  }

  /** 加载本地关键词表 */
  loadKeywordTable() {
    try {
      const file = path.join(__dirname, "resources", "memes.json")
      const raw = JSON.parse(fs.readFileSync(file, "utf8"))
      for (const item of raw) {
        for (const kw of item.keywords || []) {
          if (!bq[kw]) bq[kw] = item
        }
      }
      // 长关键词优先匹配
      const keys = Object.keys(bq).sort((a, b) => b.length - a.length)
      reg = new RegExp(`^(${keys.map(escapeRegExp).join("|")})`)
      logger.info(`[${PLUGIN_NAME}] 已加载 ${raw.length} 个表情 / ${keys.length} 个关键词`)
    } catch (err) {
      logger.error(`[${PLUGIN_NAME}] 关键词表加载失败: ${err.message}`)
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
    let svc = "不可用"
    try {
      const r = await fetch(`${SERVICE}/health`, { timeout: 5000 })
      const j = await r.json()
      svc = `正常(内置 ${j.memes} 个表情 / ${j.images_on_disk} 张素材)`
    } catch { /* 保持"不可用" */ }
    return e.reply(
      `表情功能：${kg ? "已开启" : "已关闭"}\n` +
        `本地表情：${total} 个 / 关键词 ${Object.keys(bq).length} 个\n` +
        `渲染服务：${svc}`
    )
  }

  async onList(e) {
    const keys = [...new Set(Object.values(bq).map((i) => i.key))].sort()
    const text =
      `共 ${keys.length} 个表情，发送「表情包搜索 关键词」查看用法\n\n` +
      keys.join("  ")
    return e.reply(text)
  }

  async onSearch(e, keyword) {
    const kw = (keyword || "").trim()
    const item = bq[kw]
    if (!item) {
      const found = [...new Set(Object.values(bq).filter((i) => i.key.includes(kw) || (i.keywords || []).some((k) => k.includes(kw))))]
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
    return e.reply(
      `表情：${(item.keywords || []).join(" / ")}\n` +
        `key: ${item.key}\n` +
        `需要：${need.length ? need.join("，") : "什么都不用，直接发就行"}`
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

    // 拆词:第一个 token 是「关键词 @某人 文字...」
    const tokens = msg.split(" ").filter((t) => t !== "")
    let rest = tokens.slice(1)

    // 如果第一个 token 里就粘着 @某人(例如 "摸@12345"),拆出来
    let atFromToken = null
    if (rest.length && rest[0].includes("@")) {
      const m = rest[0].match(/@(\w+)/)
      if (m) {
        atFromToken = m[1]
        rest[0] = rest[0].replace(/@(\w+)/, "")
        if (rest[0] === "") rest.shift()
      }
    }

    // 关键字后面紧跟的非 ASCII 字符视为非法触发(避免误伤正常聊天)
    if (tokens[0] !== match) return

    // 取被艾特的人
    const atId = atFromToken || e.at || e.user_id
    let userName = ""
    let avatarUrl = null

    const pick = await this.pickUser(e, atId)
    if (pick) {
      userName = pick.name || ""
      avatarUrl = pick.avatar || null
    }
    if (!avatarUrl) {
      avatarUrl = `http://q2.qlogo.cn/headimg_dl?dst_uin=${atId}&spec=5`
    }

    // 组装图片
    const images = []

    // 1) 引用消息里的图片优先
    const replied = await this.getRepliedImage(e)
    if (replied) images.push(replied)

    // 2) 需要的图片数量
    const need = item.min_images || 0
    while (images.length < need) {
      if (avatarUrl) {
        const buf = await fetchAvatar(avatarUrl)
        if (buf) {
          images.push(buf)
          continue
        }
      }
      // 拿不到头像就用用户自己发的图
      const own = e.img?.[0]
      if (own) {
        const buf = await fetchAvatar(own)
        if (buf) {
          images.push(buf)
          continue
        }
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

    // 组装文字
    let texts = rest.slice()
    let rawArg = ""

    // 纯文字表情(min_texts=0)且后面还有 token:第一个 token 当参数
    if (item.min_texts === 0 && texts.length > 0) {
      rawArg = texts[0]
      texts = texts.slice(1)
    }

    const args = buildArgs(item.key, rawArg, parseUserInfos(userName))

    // options 只保留服务端认识的名字
    const supported = new Set((item.options || []).map((o) => o.name))
    const cleanArgs = {}
    for (const [k, v] of Object.entries(args)) {
      if (supported.size === 0 || supported.has(k)) cleanArgs[k] = v
    }

    try {
      const buf = await renderService({
        key: item.key,
        images,
        texts,
        args: Object.keys(cleanArgs).length ? cleanArgs : null
      })
      return e.reply(segment.image(buf))
    } catch (err) {
      logger.error(`[${PLUGIN_NAME}] 渲染 ${item.key} 失败: ${err.message}`)
      return e.reply(`表情生成失败：${err.message}`, true)
    }
  }

  /** 取用户信息(昵称/群名片 + 头像) */
  async pickUser(e, id) {
    try {
      const pick =
        (await e.group?.pickMember?.(id)) || (await e.bot?.pickFriend?.(id))
      if (!pick) return null
      const info = (await pick.getInfo?.()) || pick.info || pick
      const avatar =
        (await pick.getAvatarUrl?.()) ||
        info?.avatar ||
        (String(info?.user_id || id).length < 11
          ? `https://cdn.discordapp.com/avatars/${info?.user_id || id}/${info?.avatar?.match?.(/([a-f0-9]{32})\./)?.[1] || ""}.png`
          : `http://q2.qlogo.cn/headimg_dl?dst_uin=${id}&spec=5`)
      return {
        name: info?.card || info?.nickname || "",
        avatar
      }
    } catch {
      return null
    }
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
        if (seg.type === "image" && seg.url) return fetchAvatar(seg.url)
        if (seg.type === "file" && seg.url) return fetchAvatar(seg.url)
      }
    } catch {
      /* 拿不到就算了 */
    }
    return null
  }
}

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}