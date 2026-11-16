# 须弥写作 Web 驾驶舱设计（webui）

日期：2026-11-16
分支：feature/webui

## 定位

本机管理面板 + 确定性工具台。小说的「创作」仍由 AI Skill（Claude Code / OpenCode 里的
sumeru-* 指令）完成，webui 负责查看进度、管理章节、一键跑校验/导出脚本、生成下一步
AI 指令。webui 是旁路工具，不进 `skills/`，不改变 Skill 流程与阶段门禁。

## 技术约束

- 仅 Python 标准库（http.server / subprocess / json / pathlib），零第三方依赖
- 前端原生 HTML/CSS/JS 单页，无构建链
- 只绑定 127.0.0.1，不暴露局域网；无登录（本机工具）
- 工作目录 = server 启动时的 cwd（在小说项目目录下运行）

## 目录结构

```
webui/
├── server.py          # http.server 入口，端口 8765
├── api.py             # 路由 → 处理函数（纯函数，便于测试）
├── lib/
│   └── backup.py      # 章节保存自动备份（与 AGENTS.md 备份规则对齐）
├── static/
│   ├── index.html     # 单页应用
│   ├── app.js
│   └── style.css
└── README.md
```

## 功能（5 个页面）

1. **仪表盘**：进度卡（总章数/已写/字数/卷）、字数分布条形图（理想区间参考带）、
   六阶段门禁状态灯（读各 *-check.json）
2. **章节管理**：章节列表（缺章/命名错误标红）+ 只读/编辑视图 + 实时字数 +
   保存走自动备份 + 细纲对照面板
3. **工具面板**：8 个脚本的参数化调用（串行执行、60s 超时、导出 300s），
   显示 stdout/退出码徽章 + 报告查看器
4. **导出中心**：平台 × 格式选择 → build.py → publish/ 产物下载链接
5. **指令助手**：按门禁状态推断下一步 /sumeru-* 指令，一键复制（纯规则，无模型调用）

## API

```
GET  /api/status                   仪表盘聚合数据（每次现算，无缓存）
GET  /api/chapters                 章节列表（含校验标记）
GET  /api/chapters/{num}           单章内容 + 细纲对照
PUT  /api/chapters/{num}           保存章节（先备份再写回）
GET  /api/outline?chapter={num}    细纲单章
POST /api/tools/{tool}             运行脚本（tool 白名单）
GET  /api/reports/{name}           报告文件（白名单）
GET  /api/export/{platform}/{file} publish/ 产物下载
GET  /api/next-step                下一步指令推断
```

安全：路径白名单（chapters/、.sumeru/、publish/），越界 403；脚本参数白名单校验；
工具串行执行（简单锁）；上传功能不做。

## 数据流原则

- **无落库**：一切以 `.sumeru/` 与文件系统为事实来源，API 每次现算，与 CLI/Agent
  侧操作保持一致
- **复用脚本**：校验逻辑全部经 subprocess 调 `skills/*/scripts/*.py`，退出码与
  JSON 报告透传，不重写业务逻辑
- 脚本非零退出 ≠ server 错误（正常返回展示）；仅 400/403/404 是 HTTP 错误

## 章节保存与备份（对齐全局规则）

- 写回前检查 `.sumeru/write/original/`：无该章 → 先存**最初原稿**（original 只存一次）
- 已有 original → 把当前版本存 `.sumeru/write/history/save-{时间戳}/`

## 测试

- `tests/test_webui.py`：直接调用 api.py 纯函数（handler 拆分），tempfile 造假项目
- 覆盖：status 聚合、章节读写、备份规则（original 不覆盖 / history 逐级保存）、
  路径穿越 403、工具执行封装（假脚本验证超时与退出码）
- 前端手动验收，CI 只跑 Python

## 实施顺序

1. 骨架（server 可启动 + 占位页）
2. lib/backup.py + 测试
3. API：status / chapters / outline
4. API：tools / reports / export
5. 前端五页（每页一提交）
6. webui/README.md + 根 README 入口

## 不做（YAGNI）

登录鉴权、多书管理、移动端适配、WebSocket、模型调用、上传。
