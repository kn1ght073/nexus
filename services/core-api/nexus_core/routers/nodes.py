"""Node registry: the hosted control plane's coordination surface.

A Node is one of the user's own machines (Mac/Windows) that can run the full
NEXUS Core and become the main server. The control plane stores only
coordination data — node name/platform, endpoint, installed services, liveness
— never personal content (that lives on the node's own disks).

Flow (guide §"Node promotion"):
1. `nexus node claim` from the machine → registers + marks it active.
2. The node heartbeats (`nexus node claim --watch` or the service loop).
3. Clients ask the control plane `GET /api/nodes/active` → endpoint to use.
4. If heartbeats stop, /active resolves to null and clients fall back to the
   control plane's auth-only surface until a node returns.
"""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import log_activity, publish_event
from ..models import Node, User, utcnow
from .relay import relay_state
from ..schemas import (
    NodeClaimRequest,
    NodeOut,
    NodeServicesRequest,
    NodeOutWithSecret,
)
from ..security import get_current_user, require_scope
from ..settings import get_settings

router = APIRouter(prefix="/nodes", tags=["nodes"])
settings = get_settings()


def _is_fresh(node: Node) -> bool:
    if node.last_seen is None:
        return False
    # last_seen is naive-UTC (SQLite) or aware-UTC (Postgres); normalize
    seen = node.last_seen.replace(tzinfo=None) if node.last_seen.tzinfo else node.last_seen
    now = utcnow().replace(tzinfo=None)
    return (now - seen).total_seconds() < settings.node_heartbeat_timeout


@router.post("/claim", response_model=NodeOutWithSecret, status_code=status.HTTP_201_CREATED)
def claim_node(
    request: NodeClaimRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register (or re-register) this machine as a node and make it active.

    Re-claiming an existing node by name rotates its api_key and demotes any
    other active node of the same user (one main server at a time).
    """
    node = (
        db.query(Node)
        .filter(Node.owner_id == current_user.id, Node.name == request.name)
        .first()
    )
    import secrets

    api_key = secrets.token_hex(24)
    if node is None:
        node = Node(name=request.name, platform=request.platform, owner_id=current_user.id)
        db.add(node)
    node.api_key = api_key
    node.endpoint = request.endpoint
    node.is_active = True
    node.last_seen = utcnow()
    # computed liveness for the response schema
    setattr(node, "is_online", True)
    # demote the user's other active nodes: single active server
    for other in db.query(Node).filter(
        Node.owner_id == current_user.id, Node.is_active.is_(True), Node.id != node.id
    ):
        other.is_active = False
    db.commit()
    db.refresh(node)
    log_activity(db, user_id=current_user.id, action="node.claimed", detail=f"{node.name} ({node.platform})")
    publish_event("NODE_CLAIMED", current_user.id, {"node_id": node.id, "name": node.name})
    db.commit()
    return node


@router.post("/{node_id}/heartbeat", response_model=NodeOut)
def heartbeat(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Keep the node marked alive (called every ~30s by the node loop)."""
    node = (
        db.query(Node)
        .filter(Node.id == node_id, Node.owner_id == current_user.id)
        .first()
    )
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    node.last_seen = utcnow()
    if not node.is_active:
        # a heartbeat means the node is back: re-activate it
        node.is_active = True
    db.commit()
    db.refresh(node)
    return node


@router.get("", response_model=list[NodeOut])
def list_nodes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    nodes = db.query(Node).filter(Node.owner_id == current_user.id).order_by(Node.last_seen.desc()).all()
    connected = relay_state.connected_node_ids()
    for n in nodes:
        setattr(n, "is_online", _is_fresh(n) or (n.id in connected))
        setattr(n, "lan_url", n.endpoint)
        setattr(n, "relay_proxy_url", f"/api/relay/{n.id}/proxy")
    return nodes


@router.get("/active", response_model=NodeOut | None)
def active_node(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resolve the current main server: active AND heartbeating (or connected to relay).

    Returns null when the node is offline — clients then stay on the control
    plane (auth + config only) until a machine claims again.
    """
    node = (
        db.query(Node)
        .filter(Node.owner_id == current_user.id, Node.is_active.is_(True))
        .first()
    )
    if node is None:
        return None

    connected = relay_state.connected_node_ids()
    is_live = _is_fresh(node) or (node.id in connected)
    if not is_live:
        return None

    setattr(node, "is_online", True)
    setattr(node, "lan_url", node.endpoint)
    setattr(node, "relay_proxy_url", f"/api/relay/{node.id}/proxy")
    return node


@router.post("/{node_id}/services", response_model=NodeOut)
def set_services(
    node_id: int,
    request: NodeServicesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_scope("admin", "devices")),
):
    """Report which optional services the node has installed (config only)."""
    node = (
        db.query(Node)
        .filter(Node.id == node_id, Node.owner_id == current_user.id)
        .first()
    )
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    node.services_json = json.dumps(request.services)
    db.commit()
    db.refresh(node)
    log_activity(db, user_id=current_user.id, action="node.services", detail=f"{node.name}: {sorted(request.services)}")
    db.commit()
    return node


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    node = (
        db.query(Node)
        .filter(Node.id == node_id, Node.owner_id == current_user.id)
        .first()
    )
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    log_activity(db, user_id=current_user.id, action="node.removed", detail=node.name)
    db.delete(node)
    db.commit()
