"""为未来接入真实语言模型预留的接口层（阶段一不启用）。

阶段一全部能力为本地实现（本地规则 + 预设模板），不调用任何外部 API、不产生费用。
未来如需接入真实模型（例如：更全面的表达反馈、更自然的对话回应、动态内容生成），
按下述协议实现一个后端并调用 register_backend() 注册即可；
业务模块（feedback / dialogue / taskgen）保持与具体模型解耦，本地模式始终可用。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ModelBackend(Protocol):
    """真实模型后端协议（未来接入点）。"""

    def generate_feedback(self, scene_id: str, answers: list[str]) -> dict[str, Any] | None:
        """对整场互动生成更全面的表达反馈；返回 None 表示回退本地规则。"""
        ...

    def dialogue_reply(self, scene_id: str, history: list[str], user_input: str) -> str | None:
        """生成对话对象的下一句回应；返回 None 表示回退本地模板。"""
        ...

    def generate_task(self, scene_id: str) -> dict[str, Any] | None:
        """动态生成学习任务；返回 None 表示回退本地模板。"""
        ...


_backend: ModelBackend | None = None


def register_backend(backend: ModelBackend | None) -> None:
    """注册（或清除，传 None）真实模型后端。"""
    global _backend
    _backend = backend


def get_backend() -> ModelBackend | None:
    """获取当前生效的模型后端；None 表示纯本地模式。"""
    return _backend
