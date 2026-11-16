# 选题数据结构

#### options.json 数据结构规范

```json
{
  "meta": {
    "generatedAt": "2026-04-26T10:00:00Z",
    "genre": "玄幻",
    "keywords": ["废柴逆袭", "系统流", "穿越"],
    "platform": "起点",
    "audience": "男频"
  },
  "options": [
    {
      "id": 1,
      "title": "书名",
      "coreConcept": "一句话概括",
      "goldenFinger": {
        "name": "金手指名称",
        "description": "金手指详细设定",
        "rules": ["规则1", "规则2"],
        "limitations": ["限制1", "限制2"],
        "growthPath": "成长路径描述"
      },
      "coreSellingPoints": ["卖点1", "卖点2", "卖点3"],
      "audience": "精准受众描述",
      "coolPointPattern": {
        "type": "打脸/升级/搞钱/恋爱/权谋",
        "rhythm": "爽点节奏描述",
        "emotionCurve": "情绪价值曲线描述"
      },
      "openingSuggestion": "前三章情节规划",
      "scores": {
        "marketHeat": 8,
        "competition": 6,
        "audienceSize": 9,
        "creationDifficulty": 5,
        "monetizationPotential": 8,
        "policyRisk": "low",
        "overallScore": 7.5
      },
      "risks": ["风险1", "风险2"],
      "differentiationStrategy": "差异化竞争策略"
    }
  ],
  "recommendedOptionId": 1,
  "marketAnalysis": {
    "trendingGenres": ["热门题材1", "热门题材2"],
    "targetGenrePerformance": "目标题材市场表现描述",
    "audienceProfile": "受众画像描述"
  }
}
```
