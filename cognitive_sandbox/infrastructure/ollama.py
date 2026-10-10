from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from cognitive_sandbox.domain.models import Agent, ConversationEvent, World


class OllamaProvider:
    def __init__(self, base_url: str, model: str, timeout: float = 90.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @property
    def label(self) -> str:
        return f"Ollama · {self.model}"

    def generate(self, world: World, agent: Agent, history: list[ConversationEvent], prompt: str) -> str:
        dialogue = "\n".join(
            f"{'玩家' if event.kind == 'player' else agent.name}: {event.content}"
            for event in history[-12:]
        )
        system = (
            f"你正在一个视觉小说世界中扮演{agent.name}（{agent.role}）。\n"
            f"世界：{world.name}。{world.description}\n"
            f"角色设定：{agent.persona}\n"
            f"世界事实：{'；'.join(world.facts)}\n"
            "用简短、自然的中文回应。不要替玩家决定行动。"
        )
        body = json.dumps({
            "model": self.model,
            "system": system,
            "prompt": f"此前对话：\n{dialogue}\n玩家：{prompt}\n请以{agent.name}的身份回应。",
            "stream": False,
        }).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/generate", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"无法连接 Ollama：{exc}") from exc
        result = payload.get("response", "")
        if not isinstance(result, str):
            raise RuntimeError("Ollama 返回了无法识别的响应。")
        return result


class DemoProvider:
    label = "本地演示"

    def generate(self, world: World, agent: Agent, history: list[ConversationEvent], prompt: str) -> str:
        return f"{agent.name}轻轻点了点头，海风掀起桌边的旧信。\n“我听着呢。你刚才说：{prompt}”"
