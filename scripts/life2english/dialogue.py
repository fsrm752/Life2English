"""情境互动：系统扮演场景中的交流对象，与用户完成多轮英语对话。

本模块只负责对话状态管理（无 IO），由 CLI / 未来界面层驱动渲染与输入。
未来模型接入点：reply() 可替换为模型生成回应，见 life2english.model_api。
"""

from __future__ import annotations


class DialogueSession:
    """一场情境互动的状态机。"""

    # 简单的轮换呼应语（固定序列，保证可复现）
    _ACKS = ["Got it!", "Okay!", "Nice, thanks!", "Great."]

    def __init__(self, scene: dict) -> None:
        self.scene = scene
        self._dialogue = scene["dialogue"]
        self.steps: list[dict] = list(self._dialogue.get("steps", []))
        self.answers: list[str] = []
        self.step_index = 0
        self.finished = False

    # -- 基本属性 -----------------------------------------------------------

    @property
    def role_zh(self) -> str:
        return self._dialogue.get("role_zh", "对话对象")

    @property
    def opening(self) -> str:
        return self._dialogue.get("opening", "")

    @property
    def closing(self) -> str:
        return self._dialogue.get("closing", "")

    @property
    def rounds(self) -> int:
        """已完成的互动轮数（用户有效回答数）。"""
        return len(self.answers)

    # -- 流程推进 -----------------------------------------------------------

    def next_step(self) -> dict | None:
        """取下一个问题；没有问题则返回 None。"""
        if self.step_index >= len(self.steps):
            return None
        step = self.steps[self.step_index]
        self.step_index += 1
        return step

    def current_step(self) -> dict | None:
        """查看当前待回答的问题（不推进）。用于「重新回答」时恢复同一轮问题。"""
        if 0 <= self.step_index - 1 < len(self.steps):
            return self.steps[self.step_index - 1]
        return None

    def record_answer(self, text: str) -> str:
        """记录一条用户回答，返回简单的呼应语。"""
        self.answers.append(text)
        ack = self._ACKS[(len(self.answers) - 1) % len(self._ACKS)]
        return ack

    def retract_last(self) -> bool:
        """撤回上一条回答（用于「重新回答」）。

        回退轮次计数并让当前问题可再次作答；若已无回答则返回 False。
        """
        if not self.answers:
            return False
        self.answers.pop()
        if self.step_index > 0:
            self.step_index -= 1
        self.finished = False
        return True

    def end(self) -> None:
        self.finished = True
