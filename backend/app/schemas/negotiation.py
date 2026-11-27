from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Personality = Literal["aggressive", "collaborative", "risk-averse"]
Action = Literal["offer", "counter", "accept", "reject"]


class AgentDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    name: str = Field(min_length=1)
    role: str = ""
    goals: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    personality: Personality = "collaborative"
    type: Literal["human", "ai"] | None = None
    is_human: bool | None = None

    @field_validator("id", "name")
    @classmethod
    def strip_nonblank(cls, value: str) -> str:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Agent IDs and names must not be blank")
        return value


class FrontendAgentOverride(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    goals: list[str] = Field(default_factory=list)
    personality: Personality = "collaborative"

    @field_validator("id", "name")
    @classmethod
    def strip_nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Agent IDs and names must not be blank")
        return value


class FrontendNegotiationStartRequest(BaseModel):
    scenario_id: str = Field(min_length=1)
    mode: Literal["simulation", "practice"]
    user_agent_id: str | None = None
    max_rounds: int = Field(default=10, gt=0)
    parameters: dict[str, str | int | float] = Field(default_factory=dict)
    agents: list[FrontendAgentOverride] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_agent_ids(self):
        ids = [agent.id.casefold() for agent in self.agents]
        if len(ids) != len(set(ids)):
            raise ValueError("Agent IDs must be unique")
        return self


class NegotiationStartRequest(BaseModel):
    scenario: str
    mode: Literal["sim", "practice"]
    agents: list[AgentDefinition] = Field(min_length=1)
    max_rounds: int = Field(default=10, gt=0)

    @model_validator(mode="after")
    def unique_agent_ids(self):
        ids = [agent.id.casefold() for agent in self.agents if agent.id]
        names = [agent.name.casefold() for agent in self.agents]
        if len(ids) != len(set(ids)) or len(names) != len(set(names)):
            raise ValueError("Agent IDs and names must be unique")
        return self


class AgentActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str | None = None
    # Kept for the existing /start + /turn API.
    agent: str | None = None
    action: Literal["offer", "counter", "counteroffer", "accept", "reject"]
    offer: Any = None
    message: str = ""

    @model_validator(mode="after")
    def require_agent_identity(self):
        if not self.agent_id and not self.agent:
            raise ValueError("agent_id is required")
        return self


class HumanTurnEvent(BaseModel):
    type: Literal["human_turn"]
    client_action_id: str = Field(min_length=1)
    action: Action
    message: str = ""
    offer: dict[str, str | int | float] | None = None


class ClientStartEvent(BaseModel):
    type: Literal["start"]


class AgentReport(BaseModel):
    agent_id: str
    name: str
    satisfaction: float | None
    concessions_made: int | None
    notes: str | None


class ConcessionTimelinePoint(BaseModel):
    round: int
    agent_id: str
    value: float
    label: str | None


class NegotiationReport(BaseModel):
    session_id: str
    scenario_name: str
    mode: Literal["simulation", "practice"]
    status: Literal["agreement", "breakdown", "deadlock"]
    rounds_elapsed: int
    terms: dict[str, str | int | float]
    summary: str
    agents: list[AgentReport]
    concession_timeline: list[ConcessionTimelinePoint]
