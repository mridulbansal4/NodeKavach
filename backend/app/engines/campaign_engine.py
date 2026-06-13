from typing import Any
from app.models.schemas import IntelligenceGraph, NetworkRisk

def detect_campaign(case_id: str, graph: IntelligenceGraph, risk_score: float) -> NetworkRisk:
    """
    SIMULATION ENGINE: Simulates Fraud Campaign Detection.
    In a real system, this uses Louvain community detection or connected
    components over the risk-propagated graph to identify campaigns.
    """
    # Deterministic simulation based on the case_id
    community_id = f"CAMPAIGN-{hash(case_id) % 999:03d}"
    
    # Calculate simulated metrics
    size = max(2, int(risk_score / 20))
    mule_count = max(1, int(size * 0.8))
    exposure_lakhs = round(risk_score * 0.18, 1)

    return NetworkRisk(
        community_id=community_id,
        size=size,
        mean_risk=risk_score * 0.9,
        mule_count=mule_count,
        exposure_lakhs=exposure_lakhs,
        central_hubs=[case_id]
    )
