
from fastapi import APIRouter, HTTPException

from app.services.scenario_service import (
    get_all_scenarios,
    get_scenario_by_id
)

router = APIRouter(prefix="/api/scenarios", tags=["Scenarios"])


@router.get("")
def list_scenarios():
    return get_all_scenarios()


@router.get("/{scenario_id}")
def get_scenario(scenario_id: str):
    scenario = get_scenario_by_id(scenario_id)

    if scenario is None:
        raise HTTPException(
            status_code=404,
            detail="Scenario not found"
        )

    return scenario
