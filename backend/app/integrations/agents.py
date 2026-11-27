
from threading import RLock
from typing import Any, Protocol


class ReasoningAgent(Protocol):
    async def generate_turn(self, context: dict[str, Any]) -> dict[str, Any]: ...


class OfferEvaluationAgent(Protocol):
    async def evaluate_offer(self, context: dict[str, Any]) -> dict[str, Any]: ...


_lock = RLock()
_reasoning_agent: ReasoningAgent | None = None
_evaluation_agent: OfferEvaluationAgent | None = None


def configure_agents(
    reasoning_agent: ReasoningAgent | None = None,
    evaluation_agent: OfferEvaluationAgent | None = None,
) -> None:
    global _reasoning_agent, _evaluation_agent
    with _lock:
        _reasoning_agent = reasoning_agent
        _evaluation_agent = evaluation_agent


def get_reasoning_agent() -> ReasoningAgent | None:
    with _lock:
        return _reasoning_agent


def get_evaluation_agent() -> OfferEvaluationAgent | None:
    with _lock:
        return _evaluation_agent
