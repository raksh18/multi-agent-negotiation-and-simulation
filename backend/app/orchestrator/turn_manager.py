class TurnManager:
    def get_current_agent(self, state: dict):
        if state["status"] != "active":
            return None
        agents = state["agents"]
        if not agents:
            return None
        index = state["current_turn"]
        return agents[index] if 0 <= index < len(agents) else None

    def get_current_agent_type(self, state: dict):
        agent = self.get_current_agent(state)
        return agent.get("type", "human" if agent.get("is_human") else "ai") if agent else None

    def is_human_turn(self, state: dict) -> bool:
        return self.get_current_agent_type(state) == "human"

    def advance_turn(self, state: dict):
        if state["status"] != "active":
            return state
        agents = state["agents"]
        if not agents:
            state["status"] = "deadlock"
            return state
        next_index = state["current_turn"] + 1
        if next_index < len(agents):
            state["current_turn"] = next_index
        elif state["current_round"] >= state["max_rounds"]:
            state["status"] = "deadlock"
            state["termination_reason"] = "Maximum rounds reached without agreement"
        else:
            state["current_turn"] = 0
            state["current_round"] += 1
        return state

    def is_negotiation_active(self, state: dict):
        return state["status"] == "active"
