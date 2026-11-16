# WORLDBUILDER_PROGRESS.json 结构说明

位置：`.sumeru/session/WORLDBUILDER_PROGRESS.json`。这是全流程唯一的进度文件，不再另设 `status.json` / `config.json`（创作需求与配置统一存 `requirements.json`）。

## 按卷循环字段

在下方阶段级结构之外，按卷循环需要额外维护两个字段：

```json
{
  "current_volume": 2,
  "volumes": [
    {
      "volumeNumber": 1,
      "chapterStart": 1,
      "chapterEnd": 20,
      "write": "completed",
      "review": "completed",
      "polish": "completed",
      "confirmed": true,
      "manual_intervention": []
    },
    {
      "volumeNumber": 2,
      "chapterStart": 21,
      "chapterEnd": 50,
      "write": "completed",
      "review": "in_progress",
      "polish": "pending",
      "confirmed": false,
      "manual_intervention": []
    }
  ],
  "pending_review": [
    {
      "checkpoint": "D",
      "volumeNumber": 1,
      "summary": "全自动模式下修订了第12-14章细纲并重写，详见 outline-revisions.json"
    }
  ]
}
```

- `volumes[].write/review/polish` 取值：`pending` / `in_progress` / `completed` / `skipped`
- `confirmed`：卷末确认点 E 是否已通过（全自动模式下为 `false` 并在 `pending_review` 留痕）
- `manual_intervention`：本卷被标记「需人工干预」的问题编号
- `stages` 中 write / review / polish 的状态由各卷状态汇总得出：全部卷完成才是 `completed`

## 进度保存机制（WORLDBUILDER_PROGRESS.json，位于 .sumeru/session/）

```json
{
  "session_id": "session-20240315-abc123",
  "created_at": "2024-03-15T10:00:00",
  "updated_at": "2024-03-15T14:30:00",
  "current_stage": "review",
  "stages": {
    "topic": {
      "status": "completed",
      "completed_at": "2024-03-15T10:15:00",
      "output_files": [
        "选题策划报告.md",
        ".sumeru/topic/options.json"
      ]
    },
    "outline": {
      "status": "completed", 
      "completed_at": "2024-03-15T11:20:00",
      "output_files": [
        "小说大纲_玄幻系统流.md",
        ".sumeru/outline/chapter-outlines.json"
      ]
    },
    "write": {
      "status": "completed",
      "completed_at": "2024-03-15T13:45:00",
      "output_files": [
        "chapters/001-废物觉醒系统.md",
        "chapters/002-系统签到奖励.md",
        ".sumeru/write/progress.json"
      ],
      "statistics": {
        "total_chapters": 100,
        "completed_chapters": 100,
        "total_words": 520000
      }
    },
    "review": {
      "status": "completed",
      "completed_at": "2024-03-15T14:45:00",
      "output_files": [
        "剧情审查报告.md",
        ".sumeru/review/issues.json",
        ".sumeru/review/fix-plan.json",
        ".sumeru/review/outline-revisions.json",
        ".sumeru/review/bottom-line-checklist.json"
      ],
      "statistics": {
        "total_issues_found": 8,
        "critical_issues": 2,
        "issues_fixed_lightweight": 4,
        "issues_fixed_rewrite": 2,
        "outline_revisions": 1,
        "bottom_line_resolved": 2,
        "bottom_line_manual": 0
      },
      "outline_revised": true,
      "chapters_rewritten": true,
      "bottom_line_all_resolved": true
    },
    "polish": {
      "status": "in_progress",
      "started_at": "2024-03-15T15:00:00",
      "progress": "60%",
      "polish_level": "moderate",
      "style": "小白爽文"
    },
    "finalize": {
      "status": "pending"
    }
  }
}
```
