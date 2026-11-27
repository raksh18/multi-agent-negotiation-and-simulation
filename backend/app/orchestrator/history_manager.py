from datetime import datetime, timezone


class HistoryManager:

    def add_event(
        self,
        state: dict,
        agent: str,
        action: str,
        offer=None,
        message: str = "",
        agent_id: str | None = None,
        reasoning: str | None = None,
        stance: str | None = None,
    ):
        """
        Adds a new event to the negotiation history.
        """

        event = {
            "round": state["current_round"],
            "agent": agent,
            "agent_id": agent_id,
            "action": action,
            "offer": offer,
            "message": message,
            "reasoning": reasoning,
            "stance": stance,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        state["history"].append(event)

        return event

    def get_history(self, state: dict):
        """
        Returns the complete negotiation history.
        """

        return state["history"]

    def get_recent_history(self, state: dict, limit: int = 5):
        """
        Returns the most recent negotiation events.
        """

        if limit < 0:
            raise ValueError("limit must be non-negative")
        if limit == 0:
            return []
        return state["history"][-limit:]

    def clear_history(self, state: dict):
        """
        Clears the negotiation history.
        """

        state["history"] = []

        return state["history"]
