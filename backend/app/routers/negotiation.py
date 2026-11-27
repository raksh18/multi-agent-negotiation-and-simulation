import logging

from fastapi import APIRouter, HTTPException

from app.orchestrator.agent import AgentTurnError, NegotiationNotFoundError
from app.schemas.negotiation import (
    AgentActionRequest,
    FrontendNegotiationStartRequest,
    NegotiationReport,
    NegotiationStartRequest,
)
from app.services.negotiation_service import (
    get_current_turn,
    get_frontend_report,
    get_frontend_session,
    get_frontend_transcript,
    get_negotiation,
    get_negotiation_history,
    start_frontend_negotiation,
    start_negotiation,
    submit_action,
)

router = APIRouter(prefix="/api/negotiations", tags=["Negotiations"])
logger = logging.getLogger(__name__)


@router.post("/start")
def start(data: NegotiationStartRequest):
    try:
        return start_negotiation(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error starting negotiation")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.post("")
def create_frontend_negotiation(data: FrontendNegotiationStartRequest):
    try:
        return start_frontend_negotiation(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error creating negotiation")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.post("/{negotiation_id}/turn")
def submit_turn(negotiation_id: str, data: AgentActionRequest):
    try:
        return submit_action(negotiation_id, data)
    except NegotiationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Negotiation not found") from exc
    except (AgentTurnError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error submitting negotiation action")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/{negotiation_id}/transcript")
def get_transcript(negotiation_id: str):
    try:
        return get_frontend_transcript(negotiation_id)
    except NegotiationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Negotiation not found") from exc
    except Exception as exc:
        logger.exception("Unexpected error fetching transcript")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/{negotiation_id}/report", response_model=NegotiationReport)
def get_report(negotiation_id: str):
    try:
        return get_frontend_report(negotiation_id)
    except NegotiationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Negotiation not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error building negotiation report")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/{negotiation_id}/history")
def get_history(negotiation_id: str):
    try:
        return get_negotiation_history(negotiation_id)
    except NegotiationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Negotiation not found") from exc
    except Exception as exc:
        logger.exception("Unexpected error fetching negotiation history")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/{negotiation_id}/current-turn")
def current_turn(negotiation_id: str):
    try:
        return {"current_agent": get_current_turn(negotiation_id)}
    except NegotiationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Negotiation not found") from exc
    except Exception as exc:
        logger.exception("Unexpected error fetching current turn")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/{negotiation_id}/internal")
def get_internal_state(negotiation_id: str):
    """Compatibility/debug endpoint for clients of the original backend state shape."""
    try:
        return get_negotiation(negotiation_id)
    except NegotiationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Negotiation not found") from exc
    except Exception as exc:
        logger.exception("Unexpected error fetching internal negotiation state")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/{negotiation_id}")
def get_state(negotiation_id: str):
    try:
        return get_frontend_session(negotiation_id)
    except NegotiationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Negotiation not found") from exc
    except Exception as exc:
        logger.exception("Unexpected error fetching negotiation")
        raise HTTPException(status_code=500, detail="Internal server error") from exc
