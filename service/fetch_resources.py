"""
资源本地化下载器
================
meme_generator(Rust 版)的图片/字体默认从公网 CDN 实时拉取
(https://cdn.jsdelivr.net/gh/MemeCrafters/meme-generator-rs@v{VERSION}/resources/)。
一旦上游 CDN 挂掉或改版,所有 GIF 表情就会变成 ImageAssetMissing —— 这正是
earth-k 表情包"突然不好使"的同类问题。

本脚本把全部 3021 张图片 + 18 个字体一次性下载到本地 resources/ 目录,
之后服务完全离线运行,不再依赖任何上游。

用法:
    python fetch_resources.py              # 增量下载(已存在且 hash 匹配则跳过)
    python fetch_resources.py --verify     # 只校验,不下载
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

BASE_URL = "https://cdn.jsdelivr.net/gh/MemeCrafters/meme-generator-rs@v0.2.3/resources/"
RESOURCE_DIR = Path(__file__).parent / "resources"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) meme-service/1.0"}
MAX_RETRY = 3


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_list() -> dict:
    """拉取资源清单。"""
    url = BASE_URL + "resources.json"
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def download_one(kind: str, item: dict, retries: int = MAX_RETRY) -> tuple[str, bool, str]:
    """下载单个资源文件。返回 (relative_path, ok, message)。"""
    rel = item["file"]
    dest = RESOURCE_DIR / kind / rel
    expected = item["hash"]

    if dest.exists():
        if sha256_file(dest) == expected:
            return rel, True, "skip"

    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BASE_URL}{kind}/{rel}"

    last_err = ""
    for attempt in range(retries):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=90) as r:
                data = r.read()
            if hashlib.sha256(data).hexdigest() != expected:
                last_err = "hash mismatch"
                continue
            tmp = dest.with_suffix(dest.suffix + ".part")
            tmp.write_bytes(data)
            tmp.replace(dest)
            return rel, True, "ok"
        except Exception as e:  # noqa: BLE001 - 网络错误种类多,统一重试
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(1.5 * (attempt + 1))

    return rel, False, last_err


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="只校验本地资源,不下载")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    RESOURCE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] fetching resource list from {BASE_URL}")
    try:
        resources = fetch_list()
    except Exception as e:
        print(f"FATAL: cannot fetch resource list: {e}", file=sys.stderr)
        return 2

    total = len(resources["fonts"]) + len(resources["images"])
    print(f"      fonts={len(resources['fonts'])} images={len(resources['images'])} total={total}")

    print(f"[2/3] {'verifying' if args.verify else 'downloading'} -> {RESOURCE_DIR}")

    # 保存清单,供服务端做完整性自检
    (RESOURCE_DIR / "resources.json").write_text(
        json.dumps(resources, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    failed: list[tuple[str, str]] = []
    done = 0
    started = time.time()

    jobs = [("fonts", item) for item in resources["fonts"]]
    jobs += [("images", item) for item in resources["images"]]

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(download_one, kind, item)
            for kind, item in jobs
        ]
        for fut in concurrent.futures.as_completed(futures):
            rel, ok, msg = fut.result()
            done += 1
            if not ok:
                failed.append((f"{rel}", msg))
            if done % 200 == 0 or done == len(jobs):
                elapsed = time.time() - started
                rate = done / elapsed if elapsed else 0
                print(f"      {done}/{len(jobs)} ({rate:.0f}/s) failed={len(failed)}")

    print(f"[3/3] done in {time.time() - started:.1f}s, failed={len(failed)}")

    if failed:
        print("\nFAILED files:")
        for rel, msg in failed[:30]:
            print(f"  {rel}: {msg}")
        return 1

    # 统计本地占用
    fonts_n = sum(1 for _ in (RESOURCE_DIR / "fonts").rglob("*") if _.is_file())
    images_n = sum(1 for _ in (RESOURCE_DIR / "images").rglob("*") if _.is_file())
    size = sum(f.stat().st_size for f in RESOURCE_DIR.rglob("*") if f.is_file())
    print(f"\nfonts on disk : {fonts_n}")
    print(f"images on disk: {images_n}")
    print(f"total size    : {size / 1024 / 1024:.1f} MB")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())