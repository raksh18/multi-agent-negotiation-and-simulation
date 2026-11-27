import asyncio
import inspect
import logging
import math
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.integrations.agents import get_evaluation_agent, get_reasoning_agent
from app.orchestrator.agent import AgentTurnError, NegotiationNotFoundError
from app.schemas.negotiation import ClientStartEvent, HumanTurnEvent
from app.services.negotiation_service import _turn_from_event, orchestrator

router = APIRouter(prefix="/ws/negotiations", tags=["Negotiations"])
logger = logging.getLogger(__name__)
_session_drivers: dict[str, asyncio.Lock] = {}


def _driver_lock(negotiation_id: str) -> asyncio.Lock:
    # Called on the single ASGI event loop; setdefault prevents duplicate drivers.
    return _session_drivers.setdefault(negotiation_id, asyncio.Lock())


def _frontend_status(status: str) -> str:
    if status == "agreement":
        return "agreement"
    if status == "deadlock":
        return "deadlock"
    return "breakdown"


def _metrics(state: dict) -> dict[str, Any]:
    evaluation = state.get("evaluation") or {}
    evaluated = evaluation.get("agents", {}) if isinstance(evaluation, dict) else {}
    satisfaction = {
        agent_id: result["satisfaction"]
        for agent_id, result in evaluated.items()
        if isinstance(result, dict) and isinstance(result.get("satisfaction"), (int, float))
    }
    stances = {}
    for event in state["history"]:
        if event.get("stance"):
            stances[event["agent_id"]] = event["stance"]
    return {
        "round": min(state["current_round"], state["max_rounds"]),
        "max_rounds": state["max_rounds"],
        "stances": stances,
        "satisfaction": satisfaction,
    }


async def _send(websocket: WebSocket, message: dict[str, Any]) -> bool:
    try:
        await websocket.send_json(message)
        return True
    except (WebSocketDisconnect, RuntimeError):
        return False


def _ai_context(state: dict, agent: dict, evaluation: dict | None = None) -> dict[str, Any]:
    return {
        "negotiation_id": state["negotiation_id"],
        "scenario_id": state.get("scenario_id"),
        "scenario": state["scenario"],
        "parameters": state.get("parameters", {}),
        "mode": "simulation" if state["mode"] == "sim" else "practice",
        "agent": agent,
        "agents": state["agents"],
        "current_round": state["current_round"],
        "max_rounds": state["max_rounds"],
        "current_offer": state.get("current_offer"),
        "current_offer_agent_id": state.get("current_offer_agent_id"),
        "history": state["history"],
        "offer_evaluation": evaluation,
    }


async def _call_provider(method, context):
    result = method(context)
    return await result if inspect.isawaitable(result) else result


def _validate_ai_turn(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("Reasoning agent must return an object")
    action = result.get("action")
    if action not in {"offer", "counter", "counteroffer", "accept", "reject"}:
        raise ValueError("Reasoning agent returned an unsupported action")
    offer = result.get("offer")
    if action in {"offer", "counter", "counteroffer"} and not isinstance(offer, dict):
        raise ValueError("Reasoning agent must return an offer object for offer actions")
    if offer is not None and not isinstance(offer, dict):
        raise ValueError("Reasoning agent offer must be an object")
    return {
        "action": "counter" if action == "counteroffer" else action,
        "offer": offer,
        "message": str(result.get("message", "")),
        "reasoning": result.get("reasoning") if isinstance(result.get("reasoning"), str) else None,
        "stance": result.get("stance") if isinstance(result.get("stance"), str) else None,
    }


def _validated_report_evaluation(result: Any, agent_ids: set[str]) -> dict[str, Any] | None:
    """Keep report data only when supplied in the documented evaluator format."""
    if not isinstance(result, dict):
        return None
    raw_agents = result.get("agents")
    raw_timeline = result.get("concession_timeline")
    if not isinstance(raw_agents, dict) or not isinstance(raw_timeline, list):
        return None
    agents: dict[str, dict[str, Any]] = {}
    for agent_id, item in raw_agents.items():
        if agent_id not in agent_ids or not isinstance(item, dict):
            return None
        satisfaction = item.get("satisfaction")
        concessions = item.get("concessions_made")
        if satisfaction is not None and (
            isinstance(satisfaction, bool) or not isinstance(satisfaction, (int, float))
            or not math.isfinite(satisfaction) or not 0 <= satisfaction <= 100
        ):
            return None
        if concessions is not None and (isinstance(concessions, bool) or not isinstance(concessions, int) or concessions < 0):
            return None
        agents[agent_id] = {
            "satisfaction": satisfaction,
            "concessions_made": concessions,
            "notes": item.get("notes") if isinstance(item.get("notes"), str) else None,
        }
    timeline = []
    for point in raw_timeline:
        if not isinstance(point, dict) or point.get("agent_id") not in agent_ids:
            return None
        value = point.get("value")
        round_number = point.get("round")
        if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                or isinstance(round_number, bool) or not isinstance(round_number, int) or round_number < 1):
            return None
        timeline.append({
            "round": round_number,
            "agent_id": point["agent_id"],
            "value": value,
            "label": point.get("label") if isinstance(point.get("label"), str) else None,
        })
    return {"agents": agents, "concession_timeline": timeline}


async def _emit_turn_and_metrics(websocket: WebSocket, result: dict):
    event = result["event"]
    latest_state = result["state"]
    agent_by_id = {agent["id"]: agent for agent in latest_state["agents"]}
    await _send(websocket, {"type": "turn", "turn": _turn_from_event(event, agent_by_id)})
    await _send(websocket, {"type": "metrics", "metrics": _metrics(latest_state)})


async def _terminal_events(websocket: WebSocket, state: dict):
    if state["status"] == "active":
        return
    if state["status"] == "deadlock":
        await _send(websocket, {
            "type": "deadlock",
            "message": state.get("termination_reason", "Maximum rounds reached without agreement."),
        })
    await _send(websocket, {"type": "finished", "status": _frontend_status(state["status"])})


@router.websocket("/{negotiation_id}")
async def negotiation_socket(websocket: WebSocket, negotiation_id: str):
    try:
        orchestrator.get_negotiation(negotiation_id)
    except NegotiationNotFoundError:
        await websocket.accept()
        await _send(websocket, {"type": "error", "message": "Negotiation not found"})
        await websocket.close(code=4404)
        return

    await websocket.accept()
    try:
        raw_start = await websocket.receive_text()
        try:
            ClientStartEvent.model_validate_json(raw_start)
        except ValidationError as exc:
            await _send(websocket, {"type": "error", "message": f"Invalid start event: {exc.errors()[0]['msg']}"})
            await websocket.close(code=4400)
            return

        driver_lock = _driver_lock(negotiation_id)
        if driver_lock.locked():
            await _send(websocket, {"type": "error", "message": "A live connection is already controlling this negotiation."})
            await websocket.close(code=4409)
            return
        async with driver_lock:
            state = orchestrator.get_negotiation(negotiation_id)
            agent_by_id = {agent["id"]: agent for agent in state["agents"]}
            for event in state["history"]:
                if not await _send(websocket, {"type": "turn", "turn": _turn_from_event(event, agent_by_id)}):
                    return
            if not await _send(websocket, {"type": "metrics", "metrics": _metrics(state)}):
                return

            while state["status"] == "active":
                current = orchestrator.get_current_turn(negotiation_id)
                if current is None:
                    break
                if current["type"] == "human":
                    if not await _send(websocket, {"type": "awaiting_human", "agent_id": current["id"]}):
                        return
                    while True:
                        raw = await websocket.receive_text()
                        try:
                            human_event = HumanTurnEvent.model_validate_json(raw)
                        except ValidationError as exc:
                            if not await _send(websocket, {"type": "error", "message": f"Invalid human turn: {exc.errors()[0]['msg']}"}):
                                return
                            continue
                        try:
                            result = orchestrator.record_action(
                                negotiation_id=negotiation_id,
                                agent_id=current["id"],
                                action=human_event.action,
                                offer=human_event.offer,
                                message=human_event.message,
                                client_action_id=human_event.client_action_id,
                            )
                            break
                        except AgentTurnError as exc:
                            if not await _send(websocket, {"type": "error", "message": str(exc)}):
                                return
                    await _emit_turn_and_metrics(websocket, result)
                else:
                    reasoning_agent = get_reasoning_agent()
                    if reasoning_agent is None:
                        await _send(websocket, {
                            "type": "error",
                            "message": "LLM Reasoning Agent is not configured; no AI response was generated.",
                        })
                        return
                    if not await _send(websocket, {"type": "thinking", "agent_id": current["id"]}):
                        return
                    evaluation_context = None
                    if state.get("current_offer") is not None and state.get("current_offer_agent_id") != current["id"]:
                        evaluator = get_evaluation_agent()
                        if evaluator is None:
                            await _send(websocket, {
                                "type": "error",
                                "message": "Offer Evaluation Agent is not configured; no AI response was generated.",
                            })
                            return
                        try:
                            evaluation_context = await _call_provider(
                                evaluator.evaluate_offer,
                                _ai_context(state, current),
                            )
                            if not isinstance(evaluation_context, dict):
                                raise ValueError("Offer Evaluation Agent must return an object")
                            if evaluation_context.get("decision") not in {"accept", "reject", "counter", "counteroffer"}:
                                raise ValueError("Offer Evaluation Agent must return decision accept, reject, or counter")
                            report_evaluation = _validated_report_evaluation(
                                evaluation_context,
                                {agent["id"] for agent in state["agents"]},
                            )
                            if report_evaluation is not None:
                                orchestrator.store_evaluation(negotiation_id, report_evaluation)
                        except Exception:
                            logger.exception("Offer Evaluation Agent failed for negotiation %s", negotiation_id)
                            await _send(websocket, {"type": "error", "message": "Offer Evaluation Agent failed; no evaluation was fabricated."})
                            return
                    try:
                        raw_turn = await _call_provider(
                            reasoning_agent.generate_turn,
                            _ai_context(state, current, evaluation_context),
                        )
                        ai_turn = _validate_ai_turn(raw_turn)
                        if evaluation_context is not None:
                            decision = evaluation_context["decision"]
                            decision = "counter" if decision == "counteroffer" else decision
                            if ai_turn["action"] != decision:
                                raise ValueError("Reasoning Agent action conflicts with the Offer Evaluation Agent decision")
                        result = orchestrator.record_action(
                            negotiation_id=negotiation_id,
                            agent_id=current["id"],
                            action=ai_turn["action"],
                            offer=ai_turn["offer"],
                            message=ai_turn["message"],
                            reasoning=ai_turn["reasoning"],
                            stance=ai_turn["stance"],
                        )
                    except Exception as exc:
                        logger.exception("AI turn failed for negotiation %s", negotiation_id)
                        await _send(websocket, {"type": "error", "message": f"AI turn failed: {exc}"})
                        return
                    await _emit_turn_and_metrics(websocket, result)

                state = orchestrator.get_negotiation(negotiation_id)
                await _terminal_events(websocket, state)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for negotiation %s", negotiation_id)
    except Exception:
        logger.exception("Unexpected WebSocket failure for negotiation %s", negotiation_id)
        await _send(websocket, {"type": "error", "message": "Negotiation stream failed"})
    finally:
        # Keep state active and recoverable; a later start event replays history.
        pass
