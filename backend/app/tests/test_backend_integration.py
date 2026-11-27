import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.integrations.agents import configure_agents
from app.orchestrator.agent import AgentTurnError, OrchestratorAgent
from app.routers.websocket import _session_drivers
from app.services import negotiation_service
from main import app


@pytest.fixture(autouse=True)
def reset_runtime():
    negotiation_service.orchestrator = OrchestratorAgent()
    from app.routers import websocket
    websocket.orchestrator = negotiation_service.orchestrator
    _session_drivers.clear()
    configure_agents()
    yield
    configure_agents()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def start_body(mode="simulation", user_agent_id=None, max_rounds=3):
    return {
        "scenario_id": "vendor-pricing",
        "mode": mode,
        "user_agent_id": user_agent_id,
        "max_rounds": max_rounds,
        "parameters": {"product": "laptops"},
        "agents": [
            {"id": "buyer", "name": "Buyer", "goals": ["Price"], "personality": "collaborative"},
            {"id": "vendor", "name": "Vendor", "goals": ["Margin"], "personality": "aggressive"},
        ],
    }


def create_session(client, **updates):
    body = start_body(**updates)
    response = client.post("/api/negotiations", json=body)
    assert response.status_code == 200, response.text
    return response.json()["session_id"]


def test_scenario_routes_and_missing_scenario(client):
    scenarios = client.get("/api/scenarios")
    assert scenarios.status_code == 200
    assert {scenario["id"] for scenario in scenarios.json()} == {"vendor-pricing", "job-offer", "project-budget"}
    assert client.get("/api/scenarios/vendor-pricing").json()["agents"][0]["id"] == "buyer"
    assert client.get("/api/scenarios/missing").status_code == 404


def test_create_session_roundtrips_frontend_session_and_transcript(client):
    session_id = create_session(client)
    session = client.get(f"/api/negotiations/{session_id}")
    assert session.status_code == 200
    assert session.json()["session_id"] == session_id
    assert session.json()["mode"] == "simulation"
    assert [agent["id"] for agent in session.json()["agents"]] == ["buyer", "vendor"]
    assert client.get(f"/api/negotiations/{session_id}/transcript").json() == []


@pytest.mark.parametrize("scenario_id", ["vendor-pricing", "job-offer", "project-budget"])
def test_all_scenarios_accept_their_declared_required_parameters(client, scenario_id):
    scenario = client.get(f"/api/scenarios/{scenario_id}").json()
    parameters = {}
    for definition in scenario["parameters"]:
        if definition["required"]:
            parameters[definition["key"]] = 500000 if definition["type"] == "number" else "Test context"
    agents = [
        {"id": agent["id"], "name": agent["name"], "goals": agent["goals"], "personality": agent["personality"]}
        for agent in scenario["agents"]
    ]
    response = client.post("/api/negotiations", json={
        "scenario_id": scenario_id, "mode": "simulation", "user_agent_id": None,
        "max_rounds": scenario["default_max_rounds"], "parameters": parameters, "agents": agents,
    })
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("body,detail", [
    (start_body(mode="practice"), "user_agent_id"),
    (start_body(mode="practice", user_agent_id="nobody"), "user_agent_id"),
    ({**start_body(), "parameters": {}}, "required scenario parameters"),
    ({**start_body(), "agents": [start_body()["agents"][0], start_body()["agents"][0]]}, "unique"),
])
def test_create_session_validates_practice_scenario_parameters_and_agent_ids(client, body, detail):
    response = client.post("/api/negotiations", json=body)
    assert response.status_code == (422 if detail == "unique" else 400)
    assert detail in str(response.json()["detail"])


def test_practice_mode_marks_selected_human_and_validates_offer(client):
    session_id = create_session(client, mode="practice", user_agent_id="buyer")
    session = client.get(f"/api/negotiations/{session_id}").json()
    assert session["user_agent_id"] == "buyer"
    assert negotiation_service.orchestrator.get_current_turn(session_id)["id"] == "buyer"
    with pytest.raises(AgentTurnError, match="Unknown offer fields"):
        negotiation_service.orchestrator.record_action(session_id, agent_id="buyer", action="offer", offer={"wrong": 2})


def test_wrong_agent_and_accept_without_offer_are_rejected():
    orchestrator = OrchestratorAgent()
    state = orchestrator.start_negotiation("test", "sim", [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}])
    session_id = state["negotiation_id"]
    with pytest.raises(AgentTurnError, match="not this agent's turn"):
        orchestrator.record_action(session_id, agent_id="b", action="offer", offer={"x": 1})
    with pytest.raises(AgentTurnError, match="no offer"):
        orchestrator.record_action(session_id, agent_id="a", action="accept")


def test_offer_counter_accept_agreement_report_and_transcript(client):
    session_id = create_session(client)
    offer = {"unit_price": 100, "quantity": 10}
    first = client.post(f"/api/negotiations/{session_id}/turn", json={
        "agent_id": "buyer", "action": "offer", "offer": offer, "message": "Initial proposal"
    })
    assert first.status_code == 200
    counter = client.post(f"/api/negotiations/{session_id}/turn", json={
        "agent_id": "vendor", "action": "counter", "offer": {"unit_price": 110}, "message": "Counter"
    })
    assert counter.status_code == 200
    accepted = client.post(f"/api/negotiations/{session_id}/turn", json={
        "agent_id": "buyer", "action": "accept", "message": "Agreed"
    })
    assert accepted.status_code == 200
    transcript = client.get(f"/api/negotiations/{session_id}/transcript").json()
    assert [turn["action"] for turn in transcript] == ["offer", "counter", "accept"]
    assert transcript[0]["agent_id"] == "buyer"
    assert client.get(f"/api/negotiations/{session_id}/report").json()["terms"] == {"unit_price": 110}
    assert client.post(f"/api/negotiations/{session_id}/turn", json={
        "agent_id": "vendor", "action": "offer", "offer": {"unit_price": 90}
    }).status_code == 400


def test_rejection_and_round_limit_are_distinct_non_agreement_outcomes(client):
    rejected_id = create_session(client)
    client.post(f"/api/negotiations/{rejected_id}/turn", json={
        "agent_id": "buyer", "action": "offer", "offer": {"unit_price": 100}
    })
    reject = client.post(f"/api/negotiations/{rejected_id}/turn", json={
        "agent_id": "vendor", "action": "reject", "message": "No"
    })
    assert reject.status_code == 200
    assert reject.json()["state"]["status"] == "rejected"
    rejected_report = client.get(f"/api/negotiations/{rejected_id}/report").json()
    assert rejected_report["status"] == "breakdown"
    assert rejected_report["terms"] == {}

    deadlock_id = create_session(client, max_rounds=1)
    for agent_id in ("buyer", "vendor"):
        response = client.post(f"/api/negotiations/{deadlock_id}/turn", json={
            "agent_id": agent_id, "action": "offer", "offer": {"unit_price": 100}
        })
        assert response.status_code == 200
    deadlock_report = client.get(f"/api/negotiations/{deadlock_id}/report").json()
    assert deadlock_report["status"] == "deadlock"
    assert deadlock_report["terms"] == {}


def test_invalid_ids_and_active_report_status(client):
    assert client.get("/api/negotiations/missing").status_code == 404
    assert client.get("/api/negotiations/missing/transcript").status_code == 404
    assert client.get("/api/negotiations/missing/report").status_code == 404
    session_id = create_session(client)
    assert client.get(f"/api/negotiations/{session_id}/report").status_code == 409


def test_concurrent_actions_cannot_advance_same_turn_twice():
    orchestrator = negotiation_service.orchestrator
    state = orchestrator.start_negotiation("test", "sim", [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}])
    session_id = state["negotiation_id"]

    def act():
        try:
            orchestrator.record_action(session_id, agent_id="a", action="offer", offer={"amount": 1})
            return "accepted"
        except AgentTurnError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: act(), range(2)))
    assert sorted(results) == ["accepted", "rejected"]
    assert len(orchestrator.get_history(session_id)) == 1


def test_websocket_practice_human_turn_and_disconnect_recovery(client):
    session_id = create_session(client, mode="practice", user_agent_id="buyer")
    with client.websocket_connect(f"/ws/negotiations/{session_id}") as socket:
        socket.send_json({"type": "start"})
        assert socket.receive_json()["type"] == "metrics"
        assert socket.receive_json() == {"type": "awaiting_human", "agent_id": "buyer"}
        socket.send_json({
            "type": "human_turn", "client_action_id": "human-1", "action": "offer",
            "message": "Offer", "offer": {"unit_price": 100},
        })
        assert socket.receive_json()["type"] == "turn"
        assert socket.receive_json()["type"] == "metrics"
        error = socket.receive_json()
        assert error["type"] == "error"
        assert "not configured" in error["message"]
    state = negotiation_service.orchestrator.get_negotiation(session_id)
    assert len(state["history"]) == 1
    assert state["status"] == "active"


def test_websocket_disconnect_preserves_state_and_reconnect_replays_history(client):
    session_id = create_session(client, mode="practice", user_agent_id="buyer")
    with client.websocket_connect(f"/ws/negotiations/{session_id}") as socket:
        socket.send_json({"type": "start"})
        socket.receive_json()  # metrics
        assert socket.receive_json()["type"] == "awaiting_human"
        socket.send_json({
            "type": "human_turn", "client_action_id": "reconnect-1", "action": "offer",
            "message": "Saved before disconnect", "offer": {"unit_price": 125},
        })
        socket.receive_json()  # turn
        socket.receive_json()  # metrics
        socket.close()

    state = negotiation_service.orchestrator.get_negotiation(session_id)
    assert state["status"] == "active"
    assert len(state["history"]) == 1
    with client.websocket_connect(f"/ws/negotiations/{session_id}") as socket:
        socket.send_json({"type": "start"})
        assert socket.receive_json()["type"] == "turn"  # replay persisted event
        assert socket.receive_json()["type"] == "metrics"
        error = socket.receive_json()
        assert error["type"] == "error"  # missing reasoning provider remains explicit


def test_only_one_websocket_controls_a_session_at_a_time(client):
    session_id = create_session(client, mode="practice", user_agent_id="buyer")
    with client.websocket_connect(f"/ws/negotiations/{session_id}") as first:
        first.send_json({"type": "start"})
        first.receive_json()  # metrics
        assert first.receive_json()["type"] == "awaiting_human"
        with client.websocket_connect(f"/ws/negotiations/{session_id}") as second:
            second.send_json({"type": "start"})
            event = second.receive_json()
            assert event["type"] == "error"
            assert "already controlling" in event["message"]


def test_websocket_simulation_uses_injected_reasoning_agent(client):
    class StubReasoner:
        async def generate_turn(self, context):
            if context["agent"]["id"] == "buyer":
                return {"action": "offer", "offer": {"unit_price": 100}, "message": "Test proposal"}
            return {"action": "accept", "offer": None, "message": "Test acceptance"}

    class StubEvaluator:
        async def evaluate_offer(self, context):
            return {"decision": "accept"}

    configure_agents(reasoning_agent=StubReasoner(), evaluation_agent=StubEvaluator())
    session_id = create_session(client)
    with client.websocket_connect(f"/ws/negotiations/{session_id}") as socket:
        socket.send_json({"type": "start"})
        events = []
        while True:
            event = socket.receive_json()
            events.append(event["type"])
            if event["type"] == "finished":
                assert event["status"] == "agreement"
                break
    assert events == ["metrics", "thinking", "turn", "metrics", "thinking", "turn", "metrics", "finished"]
    assert len(negotiation_service.orchestrator.get_history(session_id)) == 2


def test_ai_turn_waits_for_evaluator_instead_of_inventing_decision(client):
    class StubReasoner:
        async def generate_turn(self, context):
            return {"action": "offer", "offer": {"unit_price": 100}, "message": "Test proposal"}

    configure_agents(reasoning_agent=StubReasoner())
    session_id = create_session(client)
    with client.websocket_connect(f"/ws/negotiations/{session_id}") as socket:
        socket.send_json({"type": "start"})
        while True:
            event = socket.receive_json()
            if event["type"] == "error":
                assert "Offer Evaluation Agent is not configured" in event["message"]
                break
    assert len(negotiation_service.orchestrator.get_history(session_id)) == 1
    assert negotiation_service.orchestrator.get_negotiation(session_id)["status"] == "active"


def test_evaluator_data_is_used_without_fabricating_report_metrics(client):
    class StubReasoner:
        async def generate_turn(self, context):
            if context["agent"]["id"] == "vendor":
                return {"action": "accept", "message": "Test acceptance"}
            return {"action": "offer", "offer": {"unit_price": 100}, "message": "Test proposal"}

    class StubEvaluator:
        async def evaluate_offer(self, context):
            assert context["current_offer"] == {"unit_price": 100}
            return {
                "decision": "accept",
                "agents": {
                    "buyer": {"satisfaction": 80, "concessions_made": 1, "notes": "Evaluator result"},
                    "vendor": {"satisfaction": None, "concessions_made": None, "notes": None},
                },
                "concession_timeline": [{
                    "round": 1, "agent_id": "buyer", "value": 100, "label": "Unit price"
                }],
            }

    configure_agents(reasoning_agent=StubReasoner(), evaluation_agent=StubEvaluator())
    session_id = create_session(client)
    with client.websocket_connect(f"/ws/negotiations/{session_id}") as socket:
        socket.send_json({"type": "start"})
        while True:
            event = socket.receive_json()
            if event["type"] == "finished":
                assert event["status"] == "agreement"
                break
            if event["type"] == "error":
                pytest.fail(event["message"])
    report = negotiation_service.get_frontend_report(session_id)
    assert report["agents"][0]["satisfaction"] == 80
    assert report["agents"][1]["satisfaction"] is None
    assert report["concession_timeline"][0]["label"] == "Unit price"


def test_websocket_invalid_session_and_start_event(client):
    with client.websocket_connect("/ws/negotiations/missing") as socket:
        assert socket.receive_json() == {"type": "error", "message": "Negotiation not found"}

    session_id = create_session(client)
    with client.websocket_connect(f"/ws/negotiations/{session_id}") as socket:
        socket.send_text(json.dumps({"type": "something_else"}))
        assert socket.receive_json()["type"] == "error"
