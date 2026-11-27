from copy import deepcopy
import math
from typing import Any

from app.orchestrator.agent import OrchestratorAgent
from app.schemas.negotiation import AgentActionRequest
from app.services.scenario_service import get_scenario_by_id


orchestrator = OrchestratorAgent()


def start_negotiation(data):
    return orchestrator.start_negotiation(
        scenario=data.scenario,
        mode=data.mode,
        agents=[agent.model_dump(exclude_none=True) for agent in data.agents],
        max_rounds=data.max_rounds,
    )


def start_frontend_negotiation(data):
    scenario = get_scenario_by_id(data.scenario_id)
    if scenario is None:
        raise ValueError("Scenario not found")
    if len(data.agents) != len(scenario["agents"]):
        raise ValueError("The request must include every scenario agent exactly once")

    base_by_id = {agent["id"]: agent for agent in scenario["agents"]}
    overrides = [agent.model_dump() for agent in data.agents]
    override_ids = [agent["id"] for agent in overrides]
    if len(override_ids) != len(set(override_ids)) or set(override_ids) != set(base_by_id):
        raise ValueError("Agent IDs must match the selected scenario exactly")
    if len({agent["name"].strip().casefold() for agent in overrides}) != len(overrides):
        raise ValueError("Agent names must be unique")

    required = {item["key"] for item in scenario["parameters"] if item["required"]}
    missing = sorted(key for key in required if key not in data.parameters or str(data.parameters[key]).strip() == "")
    if missing:
        raise ValueError(f"Missing required scenario parameters: {', '.join(missing)}")
    allowed = {item["key"] for item in scenario["parameters"]}
    unexpected = sorted(set(data.parameters) - allowed)
    if unexpected:
        raise ValueError(f"Unknown scenario parameters: {', '.join(unexpected)}")
    for parameter in scenario["parameters"]:
        value = data.parameters.get(parameter["key"])
        if parameter["type"] == "number" and value is not None:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Scenario parameter '{parameter['key']}' must be a number")
        elif value is not None and not isinstance(value, str):
            raise ValueError(f"Scenario parameter '{parameter['key']}' must be text")

    if data.mode == "practice":
        if data.user_agent_id not in base_by_id:
            raise ValueError("Practice mode requires a valid user_agent_id")
    elif data.user_agent_id is not None:
        raise ValueError("user_agent_id must be null in simulation mode")

    agents = []
    for override in overrides:
        base = base_by_id[override["id"]]
        human = data.mode == "practice" and override["id"] == data.user_agent_id
        agents.append({
            **deepcopy(base),
            **override,
            "type": "human" if human else "ai",
            "is_human": human,
        })

    state = orchestrator.start_negotiation(
        scenario=scenario["name"],
        mode="sim" if data.mode == "simulation" else "practice",
        agents=agents,
        max_rounds=data.max_rounds,
        scenario_id=data.scenario_id,
        scenario_name=scenario["name"],
        user_agent_id=data.user_agent_id,
        parameters=deepcopy(data.parameters),
        offer_fields=deepcopy(scenario["offer_fields"]),
        evaluation=None,
        processed_client_actions=[],
    )
    return {"session_id": state["negotiation_id"]}


def get_frontend_session(negotiation_id: str):
    state = orchestrator.get_negotiation(negotiation_id)
    return {
        "session_id": state["negotiation_id"],
        "scenario_id": state["scenario_id"],
        "scenario_name": state["scenario_name"],
        "mode": "simulation" if state["mode"] == "sim" else "practice",
        "user_agent_id": state["user_agent_id"],
        "max_rounds": state["max_rounds"],
        "agents": [
            {key: agent.get(key, default) for key, default in (
                ("id", ""), ("name", ""), ("role", ""), ("goals", []),
                ("constraints", []), ("personality", "collaborative"),
            )}
            for agent in state["agents"]
        ],
        "offer_fields": state["offer_fields"],
    }


def _turn_from_event(event: dict[str, Any], agent_by_id: dict[str, dict]):
    agent = agent_by_id.get(event["agent_id"], {})
    action = "counter" if event["action"] == "counteroffer" else event["action"]
    return {
        "round": event["round"],
        "agent_id": event["agent_id"],
        "agent_name": agent.get("name", event.get("agent", "Unknown agent")),
        "action": action,
        "message": event.get("message", ""),
        "reasoning": event.get("reasoning"),
        "stance": event.get("stance") or "unknown",
        "offer": event.get("offer"),
        "timestamp": event["timestamp"],
    }


def get_frontend_transcript(negotiation_id: str):
    state = orchestrator.get_negotiation(negotiation_id)
    agent_by_id = {agent["id"]: agent for agent in state["agents"]}
    return [_turn_from_event(event, agent_by_id) for event in state["history"]]


def get_frontend_report(negotiation_id: str):
    state = orchestrator.get_negotiation(negotiation_id)
    status = state["status"]
    if status == "active":
        raise ValueError("Report is available after negotiation ends")
    frontend_status = "agreement" if status == "agreement" else "deadlock" if status == "deadlock" else "breakdown"
    evaluation = state.get("evaluation")
    evaluated_agents = evaluation.get("agents", {}) if isinstance(evaluation, dict) else {}
    results = []
    for agent in state["agents"]:
        result = evaluated_agents.get(agent["id"], {})
        results.append({
            "agent_id": agent["id"],
            "name": agent["name"],
            "satisfaction": result.get("satisfaction"),
            "concessions_made": result.get("concessions_made"),
            "notes": result.get("notes"),
        })

    accepted_terms = state.get("agreed_terms")
    terms = deepcopy(accepted_terms) if status == "agreement" and isinstance(accepted_terms, dict) else {}
    if status == "agreement":
        summary = (
            "The negotiation ended with an accepted offer."
            if terms else "The negotiation ended with an accepted offer; structured terms were not available."
        )
    elif status == "deadlock":
        summary = state.get("termination_reason", "The negotiation reached its round limit without agreement.")
    else:
        summary = state.get("termination_reason", "The negotiation ended without agreement.")

    # Concession measurements require the teammate evaluator's scenario-specific semantics.
    timeline = evaluation.get("concession_timeline", []) if isinstance(evaluation, dict) else []
    return {
        "session_id": state["negotiation_id"],
        "scenario_name": state["scenario_name"],
        "mode": "simulation" if state["mode"] == "sim" else "practice",
        "status": frontend_status,
        "rounds_elapsed": max(0, min(state["current_round"], state["max_rounds"])),
        "terms": terms,
        "summary": summary,
        "agents": results,
        "concession_timeline": deepcopy(timeline),
    }


def submit_action(negotiation_id: str, data: AgentActionRequest):
    return orchestrator.record_action(
        negotiation_id=negotiation_id,
        agent_id=data.agent_id,
        agent=data.agent,
        action=data.action,
        offer=data.offer,
        message=data.message,
    )


def get_negotiation(negotiation_id):
    return orchestrator.get_negotiation(negotiation_id)


def get_negotiation_history(negotiation_id):
    return orchestrator.get_history(negotiation_id)


def get_current_turn(negotiation_id):
    return orchestrator.get_current_turn(negotiation_id)
