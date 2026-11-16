# 大纲数据结构

#### chapter-outlines.json 数据结构规范

```json
{
  "meta": {
    "totalChapters": 100,
    "totalWords": 300000,
    "targetWords": 300000,
    "chapterWords": 3000,
    "volumeCount": 5,
    "volumes": [
      {
        "volumeNumber": 1,
        "volumeName": "立足篇",
        "chapterStart": 1,
        "chapterEnd": 20,
        "chapterCount": 20,
        "plannedWords": 60000,
        "coreConflict": "新手村冲突与立足",
        "upgradeNode": "主角觉醒金手指",
        "turningPoint": "家族除名事件",
        "volumeHook": "祖传物品浮现异象"
      }
    ],
    "generatedAt": "2026-04-05T10:00:00Z"
  },
  "chapters": [
    {
      "chapterNumber": 1,
      "chapterTitle": "废柴少爷",
      "suggestedWords": "3000-4000",
      "coreEvent": "主角在家族中被轻视，觉醒金手指",
      "characters": ["主角", "反派少爷", "管家"],
      "plotProgression": [
        "开篇展示主角废柴处境",
        "反派上门挑衅",
        "主角意外觉醒金手指",
        "初步展现实力，震惊众人",
        "结尾埋下离开家族的伏笔"
      ],
      "coolPoint": "觉醒金手指的瞬间，初步打脸挑衅者",
      "suspense": "金手指的真正功能是什么？",
      "foreshadowing": "提到家族的神秘祖传物品",
      "connection": "承接：开篇；引出：下章测试金手指",
      "location": "家族演武场",
      "pov": "主角视角",
      "mood": "压抑→震惊→期待",
      "volumeNumber": 1
    }
  ]
}
```

> 注意：`meta.targetWords` 必填——`plan-chapters.py --validate` 的字数预算检查依赖它，示例缺省会导致该检查被静默跳过。

#### world.json 数据结构规范

```json
{
  "meta": {
    "generatedAt": "2026-04-26T10:00:00Z",
    "genre": "玄幻",
    "style": "详细"
  },
  "background": {
    "era": "时代背景（古代/现代/未来/玄幻）",
    "history": ["关键历史事件1", "关键历史事件2"],
    "coreRules": "世界本质/底层逻辑"
  },
  "powerSystem": {
    "levels": ["等级1", "等级2", "等级3"],
    "acquisition": "力量获取方式",
    "balance": "力量平衡/克制关系"
  },
  "society": {
    "politics": "政治结构",
    "economy": "经济体系",
    "classes": ["社会阶层1", "社会阶层2"],
    "culture": ["文化习俗1", "文化习俗2"],
    "taboos": ["禁忌规则1", "禁忌规则2"]
  },
  "geography": {
    "overview": "世界地图概览",
    "locations": [
      {
        "name": "虚构地名",
        "type": "主城/秘境/险地",
        "description": "地点描述",
        "factions": ["关联势力"]
      }
    ]
  }
}
```

#### characters.json 数据结构规范

```json
{
  "meta": {
    "generatedAt": "2026-04-26T10:00:00Z",
    "totalCharacters": 8
  },
  "protagonist": {
    "name": "主角姓名（虚构）",
    "age": "年龄",
    "appearance": "外貌描述",
    "identity": "身份",
    "personality": {
      "core": ["核心性格1", "核心性格2"],
      "strengths": ["优点1", "优点2"],
      "weaknesses": ["缺点1", "缺点2"],
      "catchphrase": "口头禅"
    },
    "background": "过往经历",
    "trauma": "创伤/执念",
    "goals": {
      "shortTerm": "短期目标",
      "midTerm": "中期目标",
      "longTerm": "长期目标"
    },
    "growthArc": "从XX到XX的转变",
    "goldenFinger": {
      "name": "金手指名称",
      "source": "来源",
      "description": "描述",
      "limitations": ["限制1", "限制2"],
      "growthSpace": "成长空间"
    },
    "tags": ["标签1", "标签2", "标签3"]
  },
  "supportingCharacters": [
    {
      "name": "配角姓名（虚构）",
      "relationship": "与主角关系",
      "function": "导师/伙伴/对手/红颜",
      "personality": "性格描述",
      "goal": "个人目标",
      "growthLine": "成长线",
      "interactionMode": "与主角互动模式"
    }
  ],
  "antagonists": [
    {
      "name": "反派姓名（虚构）",
      "personality": "性格描述",
      "motivation": "反派动机",
      "power": "实力层次",
      "conflict": "与主角核心冲突",
      "charm": "反派魅力点"
    }
  ]
}
```
