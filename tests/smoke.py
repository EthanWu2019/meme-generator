"""全量冒烟测试:300 个表情逐个渲染,统计成功率与失败原因。"""
import io, json, time, http.client as hc
from PIL import Image as PILImage

OUT = open(r"C:\Users\34018\smoke.txt", "w", encoding="utf-8")
def W(*a): OUT.write(" ".join(str(x) for x in a) + "\n")

_b = io.BytesIO(); PILImage.new("RGB", (240, 180), (215, 105, 105)).save(_b, "PNG")
IMG = _b.getvalue()

c = hc.HTTPConnection("127.0.0.1", 8766, timeout=120)
c.request("GET", "/memes")
meta = json.loads(c.getresponse().read())["memes"]
c.close()

def render(key, n_img, n_txt):
    B = "----sm"
    parts = []
    def f(n, v):
        parts.append(f"--{B}\r\nContent-Disposition: form-data; name=\"{n}\"\r\n\r\n{v}\r\n".encode("utf-8"))
    f("key", key)
    for i in range(n_txt):
        f("texts", f"测试{i+1}")
    for i in range(n_img):
        parts.append(f"--{B}\r\nContent-Disposition: form-data; name=\"images\"; filename=\"a{i}.png\"\r\nContent-Type: image/png\r\n\r\n".encode())
        parts.append(IMG); parts.append(b"\r\n")
    parts.append(f"--{B}--\r\n".encode())
    body = b"".join(parts)
    cc = hc.HTTPConnection("127.0.0.1", 8766, timeout=120)
    cc.request("POST", "/render", body=body,
               headers={"Content-Type": f"multipart/form-data; boundary={B}", "Content-Length": str(len(body))})
    r = cc.getresponse(); d = r.read(); cc.close()
    return r.status, d

ok = fail = 0
failures = []
known_broken = []

# 上游 meme-generator-rs 0.2.3 自身损坏、任何参数组合都渲染不了的。
# 已从 plugin/resources/memes.json 剔除,这里单独计数以免误读成新回归。
# 详见 README「已知问题」。
EXPECTED_BROKEN = {"little_angel", "loading"}
gifs = pngs = 0
t0 = time.time()
keys = sorted(meta)
for n, key in enumerate(keys, 1):
    m = meta[key]
    n_img = m["min_images"]
    n_txt = m["max_texts"]
    if m["min_images"] == 0:
        n_img = 0
    try:
        st, d = render(key, n_img, n_txt)
    except Exception as e:
        st, d = -1, str(e).encode()
    if st == 200 and len(d) > 100:
        ok += 1
        if d[:6] in (b"GIF87a", b"GIF89a"): gifs += 1
        else: pngs += 1
    elif key in EXPECTED_BROKEN:
        known_broken.append((key, st))
    else:
        fail += 1
        msg = d[:150].decode("utf-8", "replace") if st != -1 else d.decode()
        failures.append((key, st, msg))
    if n % 50 == 0:
        W(f"  ... {n}/{len(keys)} ok={ok} fail={fail} ({time.time()-t0:.0f}s)")

dt = time.time() - t0
W("")
W(f"=== TOTAL {len(keys)} memes in {dt:.0f}s ===")
W(f"  OK   : {ok}")
W(f"  FAIL : {fail}")
W(f"  GIF  : {gifs}")
W(f"  PNG  : {pngs}")
W(f"  avg  : {dt/len(keys)*1000:.0f} ms/meme")
if known_broken:
    W(f"  known-broken upstream (已从词表剔除): {len(known_broken)} -> "
      + ", ".join(k for k, _ in known_broken))
W("")
if failures:
    W("=== REGRESSIONS (unexpected) ===")
    for k, st, m in failures:
        W(f"  {k:26s} status={st} {m}")
else:
    W("=== no regressions: 所有未列入 EXPECTED_BROKEN 的表情全部渲染成功 ===")
OUT.close()