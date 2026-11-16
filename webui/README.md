# 须弥写作 · Web 驾驶舱

本机管理面板：查看进度、管理章节、一键跑校验/导出脚本、生成下一步 AI 指令。
小说的「创作」仍由 AI Skill 完成（Claude Code / OpenCode 里的 `/sumeru-*` 指令），
驾驶舱负责把项目的实时状态和确定性工具摆到你眼前。

零第三方依赖：后端仅 Python 标准库，前端原生 HTML/CSS/JS。

## 启动

```bash
cd <你的小说项目目录>          # chapters/ 和 .sumeru/ 所在目录
python3 <sumeru仓库路径>/webui/server.py
# → http://127.0.0.1:8765
```

可指定端口：`python3 server.py --port 9000`。服务只绑定 127.0.0.1，不暴露局域网。

## 功能

| 页面 | 能力 |
|------|------|
| 仪表盘 | 进度卡、六阶段门禁状态灯、章节字数分布图（过短/过长标色） |
| 章节管理 | 章节列表（命名错误标红）、只读/编辑、实时字数（统一口径）、细纲对照 |
| 工具面板 | 字数统计/章节校验/时间线校验/完稿检查/敏感词扫描/拆书分析一键运行 + 报告查看器 |
| 导出中心 | 平台 × 格式导出（md/txt/html/epub）+ 产物下载 |
| 指令助手 | 按门禁状态推断下一步 `/sumeru-*` 指令，一键复制给 AI 执行 |

## 安全与数据

- 所有文件读写限制在 `chapters/`、`.sumeru/`、`publish/` 白名单内，路径穿越返回 403
- 章节保存自动备份（与全局规则一致）：最初原稿存 `.sumeru/write/original/`（只存一次），
  每次保存前的版本存 `.sumeru/write/history/save-{时间戳}/`
- 无数据库、无缓存：界面数据每次从 `.sumeru/` 现算，与 CLI/Agent 侧操作实时一致
- 工具执行串行化（同一时刻一个脚本），60 秒超时（导出 300 秒）

## 测试

```bash
python3 -m unittest discover -s tests -v   # webui 用例在 tests/test_webui.py
```
