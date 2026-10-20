"""MemeLegacy 服务入口。

上游 meme_generator.app 在 __main__ 里调用 register_router() 给每个表情
注册一条 POST /memes/<key>/ 路由；直接 `uvicorn meme_generator.app:app`
不会跑那段代码，于是 0 路由。这里显式注册。

复用上游的 render 逻辑，两套引擎（Rust 版 8766 / Python 版 8767）接口保持一致：
    GET  /health
    GET  /memes
    POST /render
"""
import os, sys, json, time

BASE = r"D:\TRSSYUNZAI\MemePy"
os.chdir(BASE)                     # manager 用 cwd 算模块名，必须在这里启动
sys.path.insert(0, BASE)
os.environ["PYTHONPATH"] = BASE

import filetype
from fastapi import FastAPI, Form, HTTPException, Response, UploadFile
from pydantic import ValidationError

from meme_generator.compat import model_dump, type_validate_python
from meme_generator.exception import MemeGeneratorException
from meme_generator.log import setup_logger
from meme_generator.manager import _memes, load_memes

setup_logger()

# 扫描所有子包，把表情注册进 _memes
for sub in ("memes", "memes_emoji", "memes_jj", "memes_other", "memes_emoji_nsfw"):
    p = os.path.join(BASE, "meme_generator", sub)
    if os.path.isdir(p):
        load_memes(p)

print(f"[legacy] registered memes: {len(_memes)}", flush=True)

from meme_generator.meme import MemeArgsModel

app = FastAPI(title="MemeLegacy")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "engine": "python",
        "memes": len(_memes),
    }


@app.get("/memes")
async def list_memes():
    out = []
    for k in sorted(_memes):
        m = _memes[k]
        p = m.params_type
        at = p.args_type
        out.append({
            "key": k,
            "keywords": list(m.keywords),
            "min_images": p.min_images,
            "max_images": p.max_images,
            "min_texts": p.min_texts,
            "max_texts": p.max_texts,
            "default_texts": list(p.default_texts),
            "options": ([{"name": n, "type": "string"} for n in _opt_names(at)]
                        if at else []),
        })
    return {"memes": out}


def _opt_names(at):
    try:
        model = at.args_model
        return [n for n in model.model_fields]
    except Exception:
        return []


@app.post("/render")
async def render(
    key: str = Form(...),
    images: list[UploadFile] = [],
    texts: list[str] = Form([]),
    args: str = Form("{}"),
):
    m = _memes.get(key)
    if m is None:
        raise HTTPException(404, f"未知表情: {key}")

    p = m.params_type
    if not (p.min_images <= len(images) <= p.max_images):
        raise HTTPException(400,
            f"这个表情需要 {p.min_images} ~ {p.max_images} 张图片,现在有 {len(images)} 张。"
            f"艾特一个人(会取他头像)、回复一条带图的消息,或直接发图。")
    if not (p.min_texts <= len(texts) <= p.max_texts):
        raise HTTPException(400,
            f"这个表情需要 {p.min_texts} ~ {p.max_texts} 段文字,现在有 {len(texts)} 段。")

    model = MemeArgsModel
    if p.args_type:
        model = p.args_type.args_model
    try:
        args_model = type_validate_python(model, json.loads(args or "{}"))
    except (ValidationError, json.JSONDecodeError) as e:
        raise HTTPException(400, f"参数不对: {e}")

    imgs = [await f.read() for f in images]
    try:
        result = m(images=imgs, texts=[t for t in texts if t],
                   args=model_dump(args_model))
    except MemeGeneratorException as e:
        raise HTTPException(e.status_code, e.message)
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")

    content = result.getvalue() if hasattr(result, "getvalue") else bytes(result)
    mime = str(filetype.guess_mime(content)) or "image/png"
    return Response(content=content, media_type=mime)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8767, log_level="warning")