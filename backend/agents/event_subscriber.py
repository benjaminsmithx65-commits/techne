"""
WebSocket Event Subscription for Real-time Deposit Detection
Based on Revert Finance liquidator-js pattern.

Provides faster deposit detection than polling by subscribing to contract events.
"""

import asyncio
import json
import os
from typing import Callable, Optional
from datetime import datetime

try:
    import websockets
except ImportError:
    websockets = None
    print("[WebSocket] websockets package not installed - using polling fallback")


# Contract and event config
CONTRACT_ADDRESS = "0x323f98c4e05073c2f76666944d95e39b78024efd"

# Deposited event signature (keccak256 hash)
DEPOSITED_EVENT_TOPIC = "0x..."  # Will be calculated

# Event topics for monitoring (inspired by liquidator-js)
EVENT_TOPICS = {
    "Deposited": "Deposited(address,uint256,uint256)",
    "Withdrawn": "Withdrawn(address,uint256)",
    "Allocated": "Allocated(address,address,uint256)",
}


class EventSubscriber:
    """
    WebSocket-based event subscription for real-time contract monitoring.
    Falls back to polling if WebSocket unavailable.
    """
    
    def __init__(self):
        self.ws_url = os.getenv("ALCHEMY_WS_URL", "wss://base-mainnet.g.alchemy.com/v2/demo")
        self.running = False
        self.ws = None
        self.callbacks: dict = {}
        self.reconnect_delay = 5  # seconds
        
    def on_event(self, event_name: str, callback: Callable):
        """Register callback for event type"""
        self.callbacks[event_name] = callback
        print(f"[EventSubscriber] Registered callback for {event_name}")
    
    async def start(self):
        """Start WebSocket subscription"""
        if websockets is None:
            print("[EventSubscriber] WebSocket disabled - using polling")
            return
        
        self.running = True
        
        while self.running:
            try:
                await self._connect_and_subscribe()
            except Exception as e:
                print(f"[EventSubscriber] Connection error: {e}")
                if self.running:
                    print(f"[EventSubscriber] Reconnecting in {self.reconnect_delay}s...")
                    await asyncio.sleep(self.reconnect_delay)
    
    async def _connect_and_subscribe(self):
        """Connect to WebSocket and subscribe to events"""
        print(f"[EventSubscriber] Connecting to {self.ws_url[:50]}...")
        
        async with websockets.connect(self.ws_url) as ws:
            self.ws = ws
            print("[EventSubscriber] ✅ Connected")
            
            # Subscribe to contract logs
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_subscribe",
                "params": [
                    "logs",
                    {
                        "address": CONTRACT_ADDRESS,
                        # Can filter by topics here
                    }
                ]
            }
            
            await ws.send(json.dumps(subscribe_msg))
            
            # Wait for subscription confirmation
            response = await ws.recv()
            response_data = json.loads(response)
            
            if "result" in response_data:
                sub_id = response_data["result"]
                print(f"[EventSubscriber] Subscribed with ID: {sub_id}")
            else:
                print(f"[EventSubscriber] Subscription failed: {response_data}")
                return
            
            # Listen for events
            while self.running:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=30)
                    await self._handle_message(msg)
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await ws.ping()
    
    async def _handle_message(self, msg: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(msg)
            
            if "params" in data and "result" in data["params"]:
                log = data["params"]["result"]
                await self._process_log(log)
                
        except Exception as e:
            print(f"[EventSubscriber] Message handling error: {e}")
    
    async def _process_log(self, log: dict):
        """Process a contract log event"""
        topics = log.get("topics", [])
        if not topics:
            return
        
        event_signature = topics[0]
        
        # Decode event based on signature
        # For now, just check for Deposited events
        print(f"[EventSubscriber] 📨 Event received: {event_signature[:20]}...")
        
        # Parse event data
        event_data = {
            "tx_hash": log.get("transactionHash"),
            "block_number": int(log.get("blockNumber", "0"), 16),
            "address": log.get("address"),
            "data": log.get("data"),
            "topics": topics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Decode indexed parameters from topics
        if len(topics) > 1:
            # topics[1] is usually the first indexed param (user address)
            user_address = "0x" + topics[1][26:]  # Remove padding
            event_data["user"] = user_address
        
        # Call registered callback
        if "Deposited" in self.callbacks:
            await self.callbacks["Deposited"](event_data)
    
    def stop(self):
        """Stop WebSocket subscription"""
        self.running = False
        print("[EventSubscriber] Stopped")


class HybridMonitor:
    """
    Hybrid monitoring: WebSocket for real-time + Polling for reliability.
    Based on liquidator-js pattern (event-driven + 15min full scan).
    """
    
    def __init__(self, contract_monitor):
        self.contract_monitor = contract_monitor
        self.event_subscriber = EventSubscriber()
        self.poll_interval = 900  # 15 minutes for full scan
        self.last_full_scan = datetime.utcnow()
    
    async def start(self):
        """Start hybrid monitoring"""
        print("[HybridMonitor] Starting hybrid event monitoring...")
        
        # Register deposit callback
        self.event_subscriber.on_event("Deposited", self._on_deposit_event)
        
        # Start WebSocket in background
        asyncio.create_task(self.event_subscriber.start())
        
        # Start periodic full scan
        asyncio.create_task(self._periodic_scan())
    
    async def _on_deposit_event(self, event_data: dict):
        """Handle deposit event from WebSocket"""
        print(f"[HybridMonitor] 🚀 Real-time deposit detected!")
        print(f"  User: {event_data.get('user', 'unknown')[:16]}...")
        print(f"  TX: {event_data.get('tx_hash', 'unknown')[:20]}...")
        
        # Trigger immediate allocation
        # The contract monitor will handle this
        # self.contract_monitor.handle_realtime_deposit(event_data)
    
    async def _periodic_scan(self):
        """Periodic full scan for missed events"""
        while True:
            await asyncio.sleep(self.poll_interval)
            
            print(f"[HybridMonitor] 🔍 Running periodic full scan...")
            # Full scan is already done by ContractMonitor.check_for_deposits()
            self.last_full_scan = datetime.utcnow()


# Global instances
event_subscriber = EventSubscriber()
