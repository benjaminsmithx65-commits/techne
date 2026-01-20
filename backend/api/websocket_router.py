"""
WebSocket Router for Real-Time Portfolio Updates
Provides live updates for positions, transactions, and agent status
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set, List, Any
import asyncio
import json
from datetime import datetime

router = APIRouter(tags=["WebSocket"])

# Connection manager for WebSocket clients
class ConnectionManager:
    def __init__(self):
        # wallet_address -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.background_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, wallet: str):
        await websocket.accept()
        if wallet not in self.active_connections:
            self.active_connections[wallet] = set()
        self.active_connections[wallet].add(websocket)
        print(f"[WebSocket] Client connected: {wallet[:10]}...")

    def disconnect(self, websocket: WebSocket, wallet: str):
        if wallet in self.active_connections:
            self.active_connections[wallet].discard(websocket)
            if not self.active_connections[wallet]:
                del self.active_connections[wallet]
        print(f"[WebSocket] Client disconnected: {wallet[:10]}...")

    async def send_personal(self, message: dict, wallet: str):
        """Send message to all connections for a specific wallet"""
        if wallet in self.active_connections:
            disconnected = []
            for connection in self.active_connections[wallet]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            
            # Clean up disconnected clients
            for conn in disconnected:
                self.active_connections[wallet].discard(conn)

    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        for wallet, connections in self.active_connections.items():
            for connection in connections.copy():
                try:
                    await connection.send_json(message)
                except Exception:
                    connections.discard(connection)

    def get_connection_count(self) -> int:
        return sum(len(conns) for conns in self.active_connections.values())


manager = ConnectionManager()


# ============================================
# WEBSOCKET ENDPOINT
# ============================================

@router.websocket("/ws/portfolio/{wallet}")
async def websocket_portfolio(websocket: WebSocket, wallet: str):
    """
    WebSocket endpoint for real-time portfolio updates.
    
    Sends:
    - position_update: When position values change
    - transaction: New transactions
    - agent_status: Agent state changes
    - price_update: Token price changes
    - heartbeat: Every 30s to keep connection alive
    """
    await manager.connect(websocket, wallet)
    
    try:
        # Send initial state
        await websocket.send_json({
            "type": "connected",
            "wallet": wallet,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(send_heartbeat(websocket, wallet))
        
        # Start portfolio polling task (checks for changes every 10s)
        poll_task = asyncio.create_task(poll_portfolio_updates(websocket, wallet))
        
        try:
            while True:
                # Wait for messages from client
                data = await websocket.receive_json()
                
                # Handle client messages
                if data.get("type") == "subscribe":
                    # Client subscribing to specific updates
                    channels = data.get("channels", ["all"])
                    await websocket.send_json({
                        "type": "subscribed",
                        "channels": channels
                    })
                    
                elif data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
                elif data.get("type") == "refresh":
                    # Client requesting immediate refresh
                    await send_portfolio_snapshot(websocket, wallet)
                    
        except WebSocketDisconnect:
            heartbeat_task.cancel()
            poll_task.cancel()
            
    finally:
        manager.disconnect(websocket, wallet)


async def send_heartbeat(websocket: WebSocket, wallet: str):
    """Send heartbeat every 30 seconds to keep connection alive"""
    while True:
        await asyncio.sleep(30)
        try:
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception:
            break


async def poll_portfolio_updates(websocket: WebSocket, wallet: str):
    """Poll for portfolio changes every 10 seconds"""
    last_hash = ""
    
    while True:
        await asyncio.sleep(10)
        try:
            # Get current portfolio state
            snapshot = await get_portfolio_snapshot(wallet)
            
            # Simple change detection using hash
            current_hash = hash(json.dumps(snapshot, sort_keys=True, default=str))
            
            if current_hash != last_hash:
                last_hash = current_hash
                await websocket.send_json({
                    "type": "portfolio_update",
                    "data": snapshot,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            print(f"[WebSocket] Poll error for {wallet[:10]}: {e}")
            break


async def send_portfolio_snapshot(websocket: WebSocket, wallet: str):
    """Send full portfolio snapshot"""
    snapshot = await get_portfolio_snapshot(wallet)
    await websocket.send_json({
        "type": "snapshot",
        "data": snapshot,
        "timestamp": datetime.utcnow().isoformat()
    })


async def get_portfolio_snapshot(wallet: str) -> dict:
    """Get current portfolio state from various sources"""
    try:
        # In production, this would:
        # 1. Query on-chain balances
        # 2. Get LP positions
        # 3. Calculate current values
        # 4. Get pending transactions
        
        return {
            "wallet": wallet,
            "totalValue": 0,
            "positions": [],
            "pendingTransactions": [],
            "agentStatus": "active"
        }
        
    except Exception as e:
        return {
            "wallet": wallet,
            "error": str(e)
        }


# ============================================
# BROADCAST FUNCTIONS (for other parts of app)
# ============================================

async def broadcast_transaction(wallet: str, tx_data: dict):
    """Broadcast new transaction to connected clients"""
    await manager.send_personal({
        "type": "transaction",
        "data": tx_data,
        "timestamp": datetime.utcnow().isoformat()
    }, wallet)


async def broadcast_agent_status(wallet: str, agent_id: str, status: str):
    """Broadcast agent status change"""
    await manager.send_personal({
        "type": "agent_status",
        "agentId": agent_id,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }, wallet)


async def broadcast_price_update(token: str, price: float):
    """Broadcast token price update to all clients"""
    await manager.broadcast({
        "type": "price_update",
        "token": token,
        "price": price,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_allocation(wallet: str, status: str, amount: float = 0, protocol: str = "", tx_hash: str = ""):
    """Broadcast allocation event to connected clients"""
    await manager.send_personal({
        "type": f"allocation_{status}",  # allocation_pending, allocation_complete, allocation_failed
        "amount": amount,
        "protocol": protocol,
        "tx_hash": tx_hash,
        "timestamp": datetime.utcnow().isoformat()
    }, wallet.lower())
    print(f"[WebSocket] Broadcast allocation_{status} to {wallet[:10]}...")


# ============================================
# ALLOCATION WEBSOCKET ENDPOINT
# ============================================

@router.websocket("/ws/allocation/{wallet}")
async def websocket_allocation(websocket: WebSocket, wallet: str):
    """
    WebSocket endpoint for real-time allocation updates.
    Frontend connects here after deposit to get instant allocation notifications.
    """
    wallet = wallet.lower()
    await manager.connect(websocket, wallet)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Waiting for allocation...",
            "wallet": wallet,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive, wait for messages
        while True:
            try:
                # Wait for any client message (ping, etc)
                data = await asyncio.wait_for(websocket.receive_json(), timeout=120)
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except asyncio.TimeoutError:
                # Send heartbeat on timeout
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, wallet)


# Stats endpoint
@router.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket connection statistics"""
    return {
        "active_connections": manager.get_connection_count(),
        "wallets_connected": len(manager.active_connections),
        "timestamp": datetime.utcnow().isoformat()
    }
