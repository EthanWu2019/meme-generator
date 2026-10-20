# 自建表情包 (meme-generator)

云崽(Yunzai-Bot)表情包插件 + 本地渲染服务。**完全离线运行,不依赖任何第三方表情包接口。**

起因:原先用的 `earth-k-plugin` 的「土块表情」功能依赖
`https://h.winterqkl.cn/memes/` 这个第三方接口,接口一挂所有表情就全废。
本项目把渲染引擎和素材全部搬到本机,自己掌控。

---

## 架构

```
云崽插件  plugins\meme-plugin\index.js
    │  HTTP (multipart)
    ▼
本地服务  D:\TRSSYUNZAI\MemeService\app\server.py   (FastAPI, 127.0.0.1:8766)
    │
    ▼
渲染引擎  meme_generator 0.2.3 (Rust / pyo3 绑定)
    │
    ▼
本地素材  app\resources\images\ (3021 张) + fonts\ (18 个)
```

素材通过 `MEME_HOME` 环境变量指向本目录,**不联网**。

---

## 目录结构

```
meme-generator/
├─ plugin/                    # 云崽插件(拷到 Yunzai-Bot\plugins\meme-plugin\)
│  ├─ index.js                # 主插件
│  ├─ package.json
│  └─ resources/
│     └─ memes.json           # 关键词表:300 个表情 / 378 个中文关键词
│
├─ service/                   # 渲染服务(拷到 MemeService\app\)
│  ├─ server.py               # FastAPI 服务
│  ├─ fetch_resources.py      # 素材本地化下载器(一次性)
│  └─ start.bat               # 启动脚本(设 MEME_HOME 等环境变量)
│
└─ scripts/
   └─ install_3060.ps1        # 一键部署到 3060
```

---

## 部署(3060)

```powershell
# 1. 建 venv 并装依赖
uv venv D:\TRSSYUNZAI\MemeService\.venv --python 3.12
uv pip install --python D:\TRSSYUNZAI\MemeService\.venv\Scripts\python.exe `
    meme-generator fastapi uvicorn pillow

# 2. 铺文件
#    service\* -> D:\TRSSYUNZAI\MemeService\app\
#    plugin\*  -> D:\TRSSYUNZAI\Yunzai-Bot\plugins\meme-plugin\

# 3. 下载素材(一次性,约 400MB)
D:\TRSSYUNZAI\MemeService\.venv\Scripts\python.exe fetch_resources.py

# 4. 注册计划任务(SYSTEM + 开机自启 + 崩溃重启)
#    见 service/start.bat 与 scripts/install_3060.ps1
```

计划任务名:`MemeService`,监听 `127.0.0.1:8766`。

---

## 服务接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 + 素材完整性 |
| GET | `/memes` | 全部表情元数据(参数/关键词/选项) |
| GET | `/search?q=` | 按关键词搜索 |
| GET | `/render/{key}?texts=a,b` | 无图表情直接渲染 |
| POST | `/render` | `multipart`: `key` / `images[]` / `texts[]` / `args`(JSON) |

返回 `image/png` 或 `image/gif`。

---

## 触发方式

和 earth-k 的「土块表情」一致,直接平替:

| 消息 | 效果 |
|---|---|
| `摸` | 用艾特的人/自己的头像生成摸头GIF |
| `摸 @某人` | 用那个人的头像 |
| `摸 圆` | 圆形头像版本 |
| `看扁` | 压扁 + 默认文字 |
| `看扁 3` | 压扁比例 3 |
| `对称 左` / `对称 右` / `对称 上` / `对称 下` | 对称方向 |
| `5000兆 我去 洛天依` | 纯文字表情,不需要艾特 |
| `循环` / `套娃` | always 的模式参数 |
| `表情包搜索 摸` | 查用法 |
| `表情包列表` | 列出全部 300 个 |
| `表情包状态` | 开关 + 服务状态 |
| `表情包开启` / `表情包关闭` | 开关 |

---

## 为什么这样设计

1. **不用第三方接口** —— 素材和引擎都在本机,接口挂了也不影响。
2. **Rust 版而不是 Python 版** —— 上游 `meme-generator` 现在主推 0.2.x(Rust 重写),
   渲染快很多(GIF 动图尤其明显)。
3. **素材本地化是关键** —— PyPI 上的 wheel **不含**图片素材(上游 `pyproject.toml`
   里 `exclude` 掉了所有 `memes/**/*.png|gif|jpg`),默认从
   `cdn.jsdelivr.net/gh/MemeCrafters/meme-generator-rs` 实时拉。
   `fetch_resources.py` 把 3021 张图 + 18 个字体全量拉到本地并校验 SHA256,
   之后彻底离线。
4. **计划任务托管** —— Windows 上 SSH 会话起的进程会被 JobObject 杀掉,
   必须走 Task Scheduler(SYSTEM + 开机/登录双触发 + 失败重启)。

---

## 素材更新

上游更新后:

```powershell
python fetch_resources.py          # 增量:已存在且 hash 匹配的跳过
python fetch_resources.py --verify # 只校验
```

然后重启 `MemeService` 计划任务。

---

## 致谢

- [MemeCrafters/meme-generator-rs](https://github.com/MemeCrafters/meme-generator-rs) —— 渲染引擎
- [MemeCrafters/meme-generator-contrib](https://github.com/MemeCrafters/meme-generator-contrib) —— 额外表情
- 关键词表参考 [earth-k-plugin](https://gitee.com/SmallK071114/earth-k-plugin) 的 `resources/bq.json`

素材均来自网络,如有侵权请联系原作者。