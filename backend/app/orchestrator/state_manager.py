from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4


class StateManager:
    """Process-local session store with per-session mutation locks.

    Replace this store with a persistent implementation when sessions must survive
    restarts or be shared across worker processes.
    """

    def __init__(self):
        self.negotiations: dict[str, dict] = {}
        self._registry_lock = RLock()
        self._session_locks: dict[str, RLock] = {}

    def create_negotiation(
        self,
        scenario: str,
        mode: str,
        agents: list[dict],
        max_rounds: int = 10,
        **metadata,
    ) -> dict:
        negotiation_id = str(uuid4())
        normalized_agents = []
        for index, agent in enumerate(agents):
            participant = dict(agent)
            participant.setdefault("id", f"agent-{index + 1}")
            participant.setdefault("type", "ai")
            participant["is_human"] = participant["type"] == "human"
            normalized_agents.append(participant)

        state = {
            "negotiation_id": negotiation_id,
            "scenario": scenario,
            "mode": mode,
            "agents": normalized_agents,
            "current_round": 1,
            "max_rounds": max_rounds,
            "current_turn": 0,
            "status": "active",
            "current_offer": None,
            "current_offer_agent_id": None,
            "history": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            **metadata,
        }
        with self._registry_lock:
            self.negotiations[negotiation_id] = state
            self._session_locks[negotiation_id] = RLock()
        return state

    def get_negotiation(self, negotiation_id: str):
        return self.negotiations.get(negotiation_id)

    def snapshot(self, negotiation_id: str):
        with self.mutation_lock(negotiation_id):
            state = self.get_negotiation(negotiation_id)
            return deepcopy(state) if state is not None else None

    def mutation_lock(self, negotiation_id: str):
        with self._registry_lock:
            lock = self._session_locks.get(negotiation_id)
        if lock is None:
            from contextlib import nullcontext
            return nullcontext()
        return lock
