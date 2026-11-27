from datetime import datetime

import pytest
from pydantic import ValidationError

from app.orchestrator.agent import OrchestratorAgent
from app.orchestrator.history_manager import HistoryManager
from app.schemas.negotiation import AgentActionRequest, NegotiationStartRequest


def test_start_schema_validates_mode_rounds_and_agents():
    valid = {"scenario": "test", "mode": "sim", "agents": [{"name": "A"}]}
    assert NegotiationStartRequest.model_validate(valid).agents[0].name == "A"
    for update in (
        {"mode": "other"},
        {"max_rounds": 0},
        {"agents": []},
        {"agents": [{"name": " "}]},
        {"agents": [{"name": "A"}, {"name": "a"}]},
    ):
        with pytest.raises(ValidationError):
            NegotiationStartRequest.model_validate({**valid, **update})


def test_action_schema_restricts_action_type():
    with pytest.raises(ValidationError):
        AgentActionRequest(agent="A", action="maybe")


@pytest.mark.parametrize(("action", "status"), [("accept", "agreement"), ("reject", "rejected")])
def test_terminal_actions_end_negotiation(action, status):
    orchestrator = OrchestratorAgent()
    state = orchestrator.start_negotiation("test", "sim", [{"name": "A"}, {"name": "B"}])
    negotiation_id = state["negotiation_id"]
    orchestrator.record_action(negotiation_id, "A", "offer", offer={"salary": 90000})
    result = orchestrator.record_action(negotiation_id, "B", action)
    assert result["state"]["status"] == status
    assert len(result["state"]["history"]) == 2
    with pytest.raises(ValueError, match="not active"):
        orchestrator.record_action(state["negotiation_id"], "A", "offer", offer={"salary": 90000})


def test_practice_mode_marks_human_and_ai_turns():
    orchestrator = OrchestratorAgent()
    state = orchestrator.start_negotiation("test", "practice", [{"name": "Human"}, {"name": "AI"}])
    negotiation_id = state["negotiation_id"]
    assert orchestrator.get_current_agent_type(negotiation_id) == "human"
    assert orchestrator.get_current_turn(negotiation_id)["is_human"] is True
    orchestrator.record_action(negotiation_id, "Human", "offer", offer=10)
    assert orchestrator.get_current_agent_type(negotiation_id) == "ai"
    assert orchestrator.get_current_turn(negotiation_id)["is_human"] is False


def test_history_timestamp_and_recent_limits():
    manager = HistoryManager()
    state = {"current_round": 1, "history": []}
    event = manager.add_event(state, "A", "offer")
    parsed = datetime.fromisoformat(event["timestamp"])
    assert parsed.utcoffset() is not None
    assert manager.get_recent_history(state, 0) == []
    with pytest.raises(ValueError):
        manager.get_recent_history(state, -1)
