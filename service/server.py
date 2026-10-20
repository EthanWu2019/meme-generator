"""
表情包渲染服务 (Meme Service)
==============================
云崽插件 meme-plugin 的后端。复用 meme_generator (Rust 绑定) 完成渲染,
图片/字体资源全部本地化在 resources/,不依赖任何上游 CDN。

接口:
    GET  /health              健康检查 + 资源完整性
    GET  /memes               全部表情的元数据(参数/关键词)
    GET  /search?q=xxx        按关键词搜索
    POST /render              渲染表情包 -> image/png | image/gif
    GET  /render/{key}        无图表情直接渲染(便于预览/调试)
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, Response

APP_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = APP_DIR / "resources"

app = FastAPI(title="Meme Service", version="1.0.0")

# ---------------------------------------------------------------- 懒加载引擎

_engine: dict[str, Any] = {}

# 表情 key -> {option 名: 类型},在 engine() 首次加载时填充
OPTION_TYPES: dict[str, dict[str, str]] = {}


def engine():
    """首次调用时导入 meme_generator,并做一次资源完整性自检。"""
    if _engine:
        return _engine
    try:
        import meme_generator as mg
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"meme_generator import failed: {e}") from e

    _engine["mg"] = mg
    _engine["keys"] = list(mg.get_meme_keys())
    _engine["info"] = {k: _describe(mg.get_meme(k).info) for k in _engine["keys"]}

    # option 名 -> 类型,供 _sanitize_args 校验用。
    # Rust 的 Meme 对象不暴露 .options,只能从 info 里建索引。
    global OPTION_TYPES
    OPTION_TYPES = {
        k: {o["name"]: o["type"] for o in v["options"]}
        for k, v in _engine["info"].items()
        if v["options"]
    }

    _engine["loaded"] = True
    return _engine


def _describe(info) -> dict:
    """把 MemeInfo 转成普通 dict(可 JSON 序列化)。"""
    p = info.params
    return {
        "key": info.key,
        "min_images": p.min_images,
        "max_images": p.max_images,
        "min_texts": p.min_texts,
        "max_texts": p.max_texts,
        "default_texts": list(p.default_texts),
        "keywords": list(info.keywords),
        "options": [
            {
                "name": o.name,
                "type": type(o).__name__.replace("Option", "").lower(),
                "default": getattr(o, "default", None),
                "description": getattr(o, "description", None),
                "choices": getattr(o, "choices", None),
            }
            for o in p.options
        ],
    }


# ---------------------------------------------------------------- 错误映射

def _explain(err) -> str:
    """把 meme_generator 的错误对象翻译成中文提示。

    注意:这些是 Rust 侧的 pyo3 异常类,字段名和 Python 版不一定一致,
    所以一律用 getattr 取值,缺字段时退回通用文案,绝不能在这里抛异常。
    """
    name = type(err).__name__

    def g(attr, default=None):
        return getattr(err, attr, default)

    if name == "ImageNumberMismatch":
        return (
            f"这个表情需要 {g('min', '?')} ~ {g('max', '?')} 张图片,"
            f"现在有 {g('actual', '?')} 张。"
            f"艾特一个人(会取他头像)、回复一条带图的消息、或自己发图都可以。"
        )
    if name == "TextNumberMismatch":
        return (
            f"这个表情需要 {g('min', '?')} ~ {g('max', '?')} 段文字,"
            f"现在有 {g('actual', '?')} 段。"
        )
    if name == "TextOverLength":
        return f"文字太长啦: {g('text', '')}"
    if name == "ImageAssetMissing":
        return f"缺少素材 {g('path', '?')}(需要跑 fetch_resources.py 补全资源)"
    if name in ("ImageDecodeError", "ImageEncodeError"):
        return f"图片处理失败: {g('error', '')}"
    if name == "MemeFeedback":
        return g("feedback", "") or ""
    if name == "DeserializeError":
        return f"参数解析失败: {g('error', '')}"
    return f"{name}: {err}"


def _sanitize_args(key: str, options: dict) -> dict:
    """按 /memes 声明的 option 类型过滤并转换参数。

    注意: Rust 的 Meme 对象只有 generate/info/key,没有 .options 属性,
    元数据只能从本地缓存的 /memes 数据里取(get_meme_info 已在 engine 里建好索引)。

    未知 option 名会让 Rust 侧抛 DeserializeError(而不是忽略),所以必须先裁剪,
    避免旧客户端或参数拼写错误把服务打挂。
    """
    if not options:
        return {}
    allowed = OPTION_TYPES.get(key)
    if not allowed:
        return {}

    clean = {}
    for name, value in options.items():
        t = allowed.get(name)
        if t is None:
            continue
        try:
            if t == "boolean":
                clean[name] = (
                    value.strip().lower() in ("1", "true", "yes", "on")
                    if isinstance(value, str)
                    else bool(value)
                )
            elif t == "integer":
                clean[name] = int(value)
            elif t == "float":
                clean[name] = float(value)
            else:
                clean[name] = str(value)
        except (TypeError, ValueError):
            continue
    return clean


def _render(mg, key: str, images: list[bytes], texts: list[str], options: dict):
    """同步渲染,返回 (bytes, content_type) 或抛 HTTPException。"""
    meme = mg.get_meme(key)
    if meme is None:
        raise HTTPException(404, f"未知表情: {key}")

    options = _sanitize_args(key, options)
    img_objs = [mg.Image(f"user_{i}.png", data) for i, data in enumerate(images)]
    result = meme.generate(img_objs, texts, options)

    if isinstance(result, (bytes, bytearray)):
        data = bytes(result)
        is_gif = data[:6] in (b"GIF87a", b"GIF89a")
        return data, "image/gif" if is_gif else "image/png"

    raise HTTPException(400, _explain(result))


# ---------------------------------------------------------------- 路由

@app.get("/health")
async def health():
    e = engine()
    res_file = RESOURCE_DIR / "resources.json"
    images_on_disk = 0
    if (RESOURCE_DIR / "images").is_dir():
        images_on_disk = sum(1 for p in (RESOURCE_DIR / "images").rglob("*") if p.is_file())
    return {
        "status": "ok",
        "memes": len(e["keys"]),
        "resources_json": res_file.exists(),
        "images_on_disk": images_on_disk,
    }


@app.get("/memes")
async def memes():
    e = engine()
    return {"count": len(e["keys"]), "memes": e["info"]}


@app.get("/search")
async def search(q: str = Query("", description="关键词")):
    e = engine()
    if not q:
        return {"query": q, "results": []}
    keys = e["mg"].search_memes(q)
    return {"query": q, "results": [e["info"][k] for k in keys if k in e["info"]]}


@app.get("/render/{key}")
async def render_simple(key: str, texts: str = Query("", description="逗号分隔的文字")):
    e = engine()
    tl = [t for t in texts.split(",") if t] if texts else []
    try:
        data, ctype = _render(e["mg"], key, [], tl, {})
    except HTTPException:
        raise
    return Response(content=data, media_type=ctype)


@app.post("/render")
async def render(
    images: list[UploadFile] = File(default=[]),
    texts: list[str] = Form(default=[]),
    args: str = Form(default=""),
    key: str = Form(...),
):
    """渲染表情包。

    - images: 0..N 张图片
    - texts : 0..N 段文字
    - args  : JSON 字符串,透传给 meme_generator 的 options
    - key   : 表情 key(或关键词,服务端会解析)
    """
    e = engine()
    mg = e["mg"]

    # key 可以是关键词
    if key not in e["info"]:
        found = mg.search_memes(key)
        if not found:
            raise HTTPException(404, f"未知表情或关键词: {key}")
        key = found[0]

    img_bytes: list[bytes] = []
    for f in images:
        img_bytes.append(await f.read())

    options: dict = {}
    if args:
        try:
            options = json.loads(args)
        except json.JSONDecodeError as ex:
            raise HTTPException(400, f"args 不是合法 JSON: {ex}") from ex

    # options 里只保留该表情真正支持的选项,防止 pyo3 抽取出错
    meta = e["info"][key]
    valid = {o["name"]: o for o in meta["options"]}
    filtered = {k: v for k, v in options.items() if k in valid}
    dropped = [k for k in options if k not in valid]
    if dropped:
        print(f"[warn] {key}: dropped unsupported options {dropped}", flush=True)

    try:
        data, ctype = _render(mg, key, img_bytes, list(texts), filtered)
    except HTTPException:
        raise
    except Exception as ex:  # noqa: BLE001
        traceback.print_exc()
        raise HTTPException(500, f"渲染异常: {type(ex).__name__}: {ex}") from ex

    return Response(content=data, media_type=ctype)


@app.exception_handler(HTTPException)
async def http_exc(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("MEME_PORT", "8766"))
    host = os.environ.get("MEME_HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port, log_level="warning")