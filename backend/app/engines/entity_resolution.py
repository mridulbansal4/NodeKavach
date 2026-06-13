from typing import Any

from app.models.schemas import IntelligenceNode, IntelligenceLink, IntelligenceGraph, NetworkRisk

def extract_entities(case_id: str, features: dict[str, Any]) -> IntelligenceGraph:
    """
    SIMULATION ENGINE: Simulates Entity Resolution.
    In a real system, this would query Neo4j or ArangoDB. Here, we build a
    deterministic simulated local star graph from the case_id and its features.
    """
    nodes = []
    links = []

    # Center node
    nodes.append(IntelligenceNode(
        id=case_id,
        type="entity",
        label=case_id,
        attributes={"standing": features.get("F3889", "unknown")}
    ))

    # Shared IP node
    ip_hash = f"IP-{hash(case_id) % 9999:04d}"
    nodes.append(IntelligenceNode(
        id=ip_hash,
        type="ip",
        label=ip_hash
    ))
    links.append(IntelligenceLink(source=case_id, target=ip_hash, type="shares_ip"))

    # Shared Device node
    device_hash = f"DEV-{hash(case_id + 'dev') % 999:03d}"
    nodes.append(IntelligenceNode(
        id=device_hash,
        type="device",
        label=device_hash
    ))
    links.append(IntelligenceLink(source=case_id, target=device_hash, type="shares_device"))

    # Counterparty
    cp_hash = f"CP-{hash(case_id + 'cp') % 9999:04d}"
    nodes.append(IntelligenceNode(
        id=cp_hash,
        type="counterparty",
        label=cp_hash
    ))
    links.append(IntelligenceLink(source=case_id, target=cp_hash, type="transferred_to"))

    return IntelligenceGraph(nodes=nodes, links=links)
