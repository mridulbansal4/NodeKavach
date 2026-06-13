from typing import Any
from app.models.schemas import IntelligenceGraph, IntelligenceNode

def propagate_risk(graph: IntelligenceGraph, base_risk: float) -> IntelligenceGraph:
    """
    SIMULATION ENGINE: Simulates Risk Propagation (PageRank-style risk flow).
    In a real system, this runs a Graph Neural Network or iterative risk 
    propagation algorithm over the resolved entity graph.
    """
    # Simply mutate the simulated graph nodes based on the base risk
    for node in graph.nodes:
        if node.type == "entity":
            node.risk_score = base_risk
            node.is_mule = base_risk >= 60.0
        elif node.type == "counterparty":
            # Counterparty inherits 40% of the risk
            node.risk_score = base_risk * 0.4
        else:
            # IPs and Devices get a flat network risk score
            node.risk_score = min(100.0, base_risk * 0.8)
    
    return graph
