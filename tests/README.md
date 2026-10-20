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

统计成功率 / GIF 与 PNG 分布 / 平均耗时，300 个约需 1-3 分钟。

期望结尾：

```
  OK   : 298
  FAIL : 0
  known-broken upstream (已从词表剔除): 2 -> little_angel, loading
=== no regressions: 所有未列入 EXPECTED_BROKEN 的表情全部渲染成功 ===
```

`FAIL` 只统计**真实回归**。`little_angel` / `loading` 是上游 0.2.3 自身损坏
（见主 README「已知问题」），脚本里用 `EXPECTED_BROKEN` 单独归类，
上游修复后从该集合移除即可。
