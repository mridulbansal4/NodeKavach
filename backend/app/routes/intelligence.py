from fastapi import APIRouter, HTTPException
from typing import Any

from app.models.schemas import IntelligenceGraph, NetworkRisk
from app.engines.entity_resolution import extract_entities
from app.engines.risk_propagation import propagate_risk
from app.engines.campaign_engine import detect_campaign

# Simple mock cache to retrieve features for an account, 
# simulating what would normally be passed from the case store.
# In a real system, we'd look this up from a database.
from app.database.case_store import STORE

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

@router.get("/{case_id}/graph", response_model=IntelligenceGraph)
def get_entity_graph(case_id: str):
    """
    Returns the resolved entity graph and propagated risk for an account.
    """
    case = STORE.get_case(case_id)
    if not case:
        # Fallback to an empty mock graph if we can't find it
        return extract_entities(case_id, {})
    
    analysis = case.analysis
    if not analysis:
        return extract_entities(case_id, {})
    
    # Normally we'd need raw features, but we can just use the score for simulation
    graph = extract_entities(case_id, {})
    propagated = propagate_risk(graph, analysis.risk_score)
    return propagated

@router.get("/{case_id}/campaign", response_model=NetworkRisk)
def get_campaign(case_id: str):
    """
    Returns the campaign network metrics for an account.
    """
    case = STORE.get_case(case_id)
    score = case.risk_score if case else 50.0
    
    graph = extract_entities(case_id, {})
    return detect_campaign(case_id, graph, score)
