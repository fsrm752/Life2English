"""Life2English — 生活场景驱动的英语学习 Skill（核心包）。

核心闭环：
    场景输入 → 场景识别 → 学习任务生成 → 情境互动 → 表达反馈 → 迁移练习 → 学习总结

阶段一说明：
- 全部逻辑为本地实现（本地规则 + 预设模板），不调用任何外部模型 API，不产生费用。
- 未来接入真实语言模型的预留接口见 life2english.model_api。
"""

__version__ = "0.1.0"
__all__ = [
    "store",
    "scenario",
    "taskgen",
    "feedback",
    "dialogue",
    "transfer",
    "summary",
    "session",
    "model_api",
]
