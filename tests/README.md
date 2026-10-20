# 测试

在 3060 上跑（服务需已启动在 127.0.0.1:8766）。

## regress.mjs —— 插件端到端回归（23 项）

```powershell
& "C:\Users\34018\AppData\Local\nvm\v20.11.1\node.exe" tests\regress.mjs
```

覆盖：无空格 `@某人`、中文昵称艾特、误触防护（摸鱼/摸黑）、
参数生效性（不同参数必须产出不同 md5）、三个管理指令。

期望输出结尾：`=== 23 passed, 0 failed ===`

## smoke.py —— 全量冒烟（300 个表情逐个实渲）

```powershell
D:\TRSSYUNZAI\MemeService\.venv\Scripts\python.exe tests\smoke.py
type C:\Users\34018\smoke.txt
```

统计成功率 / GIF 与 PNG 分布 / 平均耗时，失败项列在末尾。
300 个约需 1-3 分钟。
