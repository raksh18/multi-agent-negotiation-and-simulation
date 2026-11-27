from copy import deepcopy
import math

from app.orchestrator.history_manager import HistoryManager
from app.orchestrator.state_manager import StateManager
from app.orchestrator.turn_manager import TurnManager


class NegotiationNotFoundError(ValueError):
    pass


class AgentTurnError(ValueError):
    pass


class OrchestratorAgent:
    def __init__(self):
        self.state_manager = StateManager()
        self.turn_manager = TurnManager()
        self.history_manager = HistoryManager()

    def start_negotiation(
        self,
        scenario: str,
        mode: str,
        agents: list,
        max_rounds: int = 10,
        **metadata,
    ):
        if mode not in {"sim", "simulation", "practice"}:
            raise ValueError("Unsupported negotiation mode")
        if len(agents) < 2:
            raise ValueError("A negotiation requires at least two agents")
        normalized = []
        ids = set()
        names = set()
        for index, raw in enumerate(agents):
            participant = dict(raw)
            participant["id"] = str(participant.get("id") or f"agent-{index + 1}").strip()
            participant["name"] = str(participant.get("name") or "").strip()
            if not participant["id"] or not participant["name"]:
                raise ValueError("Every agent must have a non-empty ID and name")
            if participant["id"].casefold() in ids:
                raise ValueError("Agent IDs must be unique")
            if participant["name"].casefold() in names:
                raise ValueError("Agent names must be unique")
            ids.add(participant["id"].casefold())
            names.add(participant["name"].casefold())
            if mode in {"sim", "simulation"}:
                participant["type"] = "ai"
            else:
                participant["type"] = participant.get("type", "human" if index == 0 else "ai")
                if participant["type"] not in {"human", "ai"}:
                    raise ValueError("Agent type must be human or ai")
            participant["is_human"] = participant["type"] == "human"
            normalized.append(participant)

        if mode == "practice" and sum(a["is_human"] for a in normalized) != 1:
            raise ValueError("Practice mode requires exactly one human agent")

        return self.state_manager.create_negotiation(
            scenario=scenario,
            mode="sim" if mode == "simulation" else mode,
            agents=normalized,
            max_rounds=max_rounds,
            **metadata,
        )

    def _state(self, negotiation_id: str):
        state = self.state_manager.get_negotiation(negotiation_id)
        if state is None:
            raise NegotiationNotFoundError("Negotiation not found")
        return state

    def get_current_turn(self, negotiation_id: str):
        state = self._state(negotiation_id)
        with self.state_manager.mutation_lock(negotiation_id):
            return deepcopy(self.turn_manager.get_current_agent(state))

    def get_current_agent_type(self, negotiation_id: str):
        state = self._state(negotiation_id)
        with self.state_manager.mutation_lock(negotiation_id):
            return self.turn_manager.get_current_agent_type(state)

    def record_action(
        self,
        negotiation_id: str,
        agent: str | None = None,
        action: str = "",
        offer=None,
        message: str = "",
        agent_id: str | None = None,
        reasoning: str | None = None,
        stance: str | None = None,
        client_action_id: str | None = None,
    ):
        state = self._state(negotiation_id)
        with self.state_manager.mutation_lock(negotiation_id):
            if state["status"] != "active":
                raise AgentTurnError("Negotiation is not active")
            processed_ids = state.setdefault("processed_client_actions", [])
            if client_action_id and client_action_id in processed_ids:
                raise AgentTurnError("Duplicate human action")
            current = self.turn_manager.get_current_agent(state)
            if current is None:
                raise AgentTurnError("Negotiation has no current agent")
            supplied = agent_id or agent
            if supplied not in {current["id"], current["name"]}:
                raise AgentTurnError("It is not this agent's turn")
            normalized_action = "counteroffer" if action == "counter" else action
            if normalized_action not in {"offer", "counteroffer", "accept", "reject"}:
                raise AgentTurnError("Unsupported action")
            if normalized_action in {"offer", "counteroffer"} and offer is None:
                raise AgentTurnError("An offer is required for offer and counteroffer actions")
            if normalized_action in {"offer", "counteroffer"} and state.get("offer_fields"):
                if not isinstance(offer, dict) or not offer:
                    raise AgentTurnError("Offer must contain at least one scenario term")
                fields = {field["key"]: field for field in state["offer_fields"]}
                unknown = set(offer) - set(fields)
                if unknown:
                    raise AgentTurnError(f"Unknown offer fields: {', '.join(sorted(unknown))}")
                for key, value in offer.items():
                    field_type = fields[key]["type"]
                    if field_type == "number" and (
                        isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                    ):
                        raise AgentTurnError(f"Offer field '{key}' must be numeric")
                    if field_type == "text" and not isinstance(value, str):
                        raise AgentTurnError(f"Offer field '{key}' must be text")
            if normalized_action == "accept":
                if state["current_offer"] is None:
                    raise AgentTurnError("There is no offer to accept")
                if state["current_offer_agent_id"] == current["id"]:
                    raise AgentTurnError("An agent cannot accept its own offer")
                accepted_offer = deepcopy(state["current_offer"])
            else:
                accepted_offer = None

            if normalized_action in {"offer", "counteroffer"}:
                state["current_offer"] = deepcopy(offer)
                state["current_offer_agent_id"] = current["id"]

            event = self.history_manager.add_event(
                state=state,
                agent=current["name"],
                agent_id=current["id"],
                action=normalized_action,
                offer=deepcopy(offer),
                message=message,
                reasoning=reasoning,
                stance=stance,
            )
            if normalized_action == "accept":
                state["status"] = "agreement"
                state["agreed_terms"] = accepted_offer
            elif normalized_action == "reject":
                state["status"] = "rejected"
                state["termination_reason"] = "An agent rejected the negotiation"
            else:
                self.turn_manager.advance_turn(state)
            if client_action_id:
                processed_ids.append(client_action_id)
            return {"event": deepcopy(event), "state": deepcopy(state)}

    def store_evaluation(self, negotiation_id: str, evaluation: dict):
        state = self._state(negotiation_id)
        with self.state_manager.mutation_lock(negotiation_id):
            state["evaluation"] = deepcopy(evaluation)
            return deepcopy(state["evaluation"])

    def get_negotiation(self, negotiation_id: str):
        state = self.state_manager.snapshot(negotiation_id)
        if state is None:
            raise NegotiationNotFoundError("Negotiation not found")
        return state

    def get_history(self, negotiation_id: str):
        return self.get_negotiation(negotiation_id)["history"]
