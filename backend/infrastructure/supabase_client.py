"""
Supabase Database Integration for Techne Finance
Provides persistent storage for positions, audit trail, and pool data.

Uses REST API directly via httpx (no native dependencies).
"""

import os
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Supabase REST API client for Techne Finance.
    
    Uses httpx for direct REST calls (no native SDK dependencies).
    
    Tables:
    - positions: User DeFi positions
    - transactions: Audit trail
    - pool_snapshots: The Graph cache
    - agent_configs: User agent configurations
    - leverage_positions: Smart Loop positions
    - harvests: Executor rewards
    """
    
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_KEY", "")
        self._initialized = bool(self.url and self.key)
        
        if self._initialized:
            logger.info(f"[Supabase] Configured for {self.url[:40]}...")
        else:
            logger.warning("[Supabase] Missing SUPABASE_URL or SUPABASE_KEY - using in-memory fallback")
    
    @property
    def is_available(self) -> bool:
        return self._initialized
    
    def _headers(self) -> dict:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    async def _request(
        self,
        method: str,
        table: str,
        data: dict = None,
        params: dict = None
    ) -> Optional[List[dict]]:
        """Make async request to Supabase REST API"""
        import time
        from infrastructure.api_metrics import api_metrics
        
        if not self.is_available:
            return None
        
        url = f"{self.url}/rest/v1/{table}"
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                if method == "GET":
                    resp = await client.get(url, headers=self._headers(), params=params)
                elif method == "POST":
                    resp = await client.post(url, headers=self._headers(), json=data)
                elif method == "PATCH":
                    resp = await client.patch(url, headers=self._headers(), json=data, params=params)
                elif method == "DELETE":
                    resp = await client.delete(url, headers=self._headers(), params=params)
                else:
                    return None
                
                response_time = time.time() - start_time
                
                if resp.status_code in [200, 201, 204]:
                    api_metrics.record_call('supabase', f'{method} /{table}', 'success', response_time)
                    return resp.json() if resp.text else []
                else:
                    api_metrics.record_call('supabase', f'{method} /{table}', 'error', response_time,
                                           error_message=f"HTTP {resp.status_code}", status_code=resp.status_code)
                    logger.error(f"[Supabase] {method} {table}: {resp.status_code}")
                    return None
                    
            except Exception as e:
                api_metrics.record_call('supabase', f'{method} /{table}', 'error', time.time() - start_time,
                                       error_message=str(e)[:200])
                logger.error(f"[Supabase] Request failed: {e}")
                return None
    
    # ==========================================
    # POSITIONS
    # ==========================================
    
    async def save_position(
        self,
        user_address: str,
        protocol: str,
        entry_value: float,
        current_value: float,
        entry_time: datetime = None,
        metadata: dict = None
    ) -> Optional[dict]:
        """Save or update a user position (upsert)"""
        data = {
            "user_address": user_address.lower(),
            "protocol": protocol,
            "entry_value": entry_value,
            "current_value": current_value,
            "entry_time": (entry_time or datetime.utcnow()).isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        # Upsert via POST with on_conflict
        headers = self._headers()
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    f"{self.url}/rest/v1/positions",
                    headers=headers,
                    json=data
                )
                if resp.status_code in [200, 201]:
                    logger.info(f"[Supabase] Position saved: {user_address[:10]}... @ {protocol}")
                    return resp.json()[0] if resp.text else data
                return None
            except Exception as e:
                logger.error(f"[Supabase] Save position failed: {e}")
                return None
    
    async def get_positions(self, user_address: str) -> List[dict]:
        """Get all positions for a user"""
        result = await self._request(
            "GET", "positions",
            params={"user_address": f"eq.{user_address.lower()}", "select": "*"}
        )
        return result or []
    
    async def delete_position(self, user_address: str, protocol: str) -> bool:
        """Delete a position"""
        result = await self._request(
            "DELETE", "positions",
            params={
                "user_address": f"eq.{user_address.lower()}",
                "protocol": f"eq.{protocol}"
            }
        )
        return result is not None
    
    # ==========================================
    # TRANSACTIONS / AUDIT
    # ==========================================
    
    async def log_transaction(
        self,
        user_address: str,
        action_type: str,
        tx_hash: Optional[str],
        details: dict,
        status: str = "completed"
    ) -> Optional[dict]:
        """Log a transaction to audit trail"""
        data = {
            "user_address": user_address.lower(),
            "action_type": action_type,
            "tx_hash": tx_hash,
            "details": details,
            "status": status,
            "created_at": datetime.utcnow().isoformat()
        }
        result = await self._request("POST", "transactions", data=data)
        return result[0] if result else None
    
    async def get_transactions(self, user_address: str, limit: int = 50) -> List[dict]:
        """Get transaction history"""
        result = await self._request(
            "GET", "transactions",
            params={
                "user_address": f"eq.{user_address.lower()}",
                "select": "*",
                "order": "created_at.desc",
                "limit": str(limit)
            }
        )
        return result or []
    
    # ==========================================
    # POOL SNAPSHOTS
    # ==========================================
    
    async def save_pool_snapshot(
        self,
        pool_name: str,
        protocol: str,
        apy: float,
        tvl: float
    ) -> Optional[dict]:
        """Save pool data from The Graph"""
        data = {
            "pool_name": pool_name,
            "protocol": protocol,
            "apy": apy,
            "tvl": tvl,
            "snapshot_time": datetime.utcnow().isoformat()
        }
        result = await self._request("POST", "pool_snapshots", data=data)
        return result[0] if result else None
    
    async def get_latest_pool_data(self, pool_name: str) -> Optional[dict]:
        """Get latest snapshot for a pool"""
        result = await self._request(
            "GET", "pool_snapshots",
            params={
                "pool_name": f"eq.{pool_name}",
                "select": "*",
                "order": "snapshot_time.desc",
                "limit": "1"
            }
        )
        return result[0] if result else None
    
    # ==========================================
    # LEVERAGE POSITIONS
    # ==========================================
    
    async def save_leverage_position(
        self,
        user_address: str,
        protocol: str,
        initial_deposit: float,
        current_collateral: float,
        current_debt: float,
        leverage: float,
        health_factor: float,
        loop_count: int
    ) -> Optional[dict]:
        """Save leverage position from Smart Loop"""
        data = {
            "user_address": user_address.lower(),
            "protocol": protocol,
            "initial_deposit": initial_deposit,
            "current_collateral": current_collateral,
            "current_debt": current_debt,
            "leverage": leverage,
            "health_factor": health_factor,
            "loop_count": loop_count,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        headers = self._headers()
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    f"{self.url}/rest/v1/leverage_positions",
                    headers=headers,
                    json=data
                )
                return resp.json()[0] if resp.status_code in [200, 201] else None
            except:
                return None
    
    async def get_leverage_positions(self, user_address: str) -> List[dict]:
        """Get leverage positions for user"""
        result = await self._request(
            "GET", "leverage_positions",
            params={"user_address": f"eq.{user_address.lower()}", "select": "*"}
        )
        return result or []
    
    # ==========================================
    # AGENT CONFIGS
    # ==========================================
    
    async def save_agent_config(self, user_address: str, config: dict) -> Optional[dict]:
        """Save agent configuration"""
        data = {
            "user_address": user_address.lower(),
            "config": config,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        headers = self._headers()
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    f"{self.url}/rest/v1/agent_configs",
                    headers=headers,
                    json=data
                )
                return resp.json()[0] if resp.status_code in [200, 201] else None
            except:
                return None
    
    async def get_agent_config(self, user_address: str) -> Optional[dict]:
        """Get agent configuration"""
        result = await self._request(
            "GET", "agent_configs",
            params={
                "user_address": f"eq.{user_address.lower()}",
                "select": "config",
                "limit": "1"
            }
        )
        return result[0].get("config") if result else None
    
    # ==========================================
    # HARVESTS
    # ==========================================
    
    async def log_harvest(
        self,
        user_address: str,
        executor_address: str,
        protocol: str,
        harvested_amount: float,
        executor_reward: float,
        tx_hash: str = None
    ) -> Optional[dict]:
        """Log a harvest with executor reward"""
        data = {
            "user_address": user_address.lower(),
            "executor_address": executor_address.lower(),
            "protocol": protocol,
            "harvested_amount": harvested_amount,
            "executor_reward": executor_reward,
            "tx_hash": tx_hash,
            "created_at": datetime.utcnow().isoformat()
        }
        result = await self._request("POST", "harvests", data=data)
        return result[0] if result else None


# Global instance
supabase = SupabaseClient()


# ==========================================
# SQL SCHEMA - Run in Supabase SQL Editor
# ==========================================
SCHEMA_SQL = """
-- Positions
CREATE TABLE IF NOT EXISTS positions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_address TEXT NOT NULL,
    protocol TEXT NOT NULL,
    entry_value DECIMAL NOT NULL,
    current_value DECIMAL NOT NULL,
    entry_time TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    UNIQUE(user_address, protocol)
);

-- Transactions (Audit Trail)
CREATE TABLE IF NOT EXISTS transactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_address TEXT NOT NULL,
    action_type TEXT NOT NULL,
    tx_hash TEXT,
    details JSONB DEFAULT '{}',
    status TEXT DEFAULT 'completed',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pool Snapshots
CREATE TABLE IF NOT EXISTS pool_snapshots (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    pool_name TEXT NOT NULL,
    protocol TEXT NOT NULL,
    apy DECIMAL,
    tvl DECIMAL,
    snapshot_time TIMESTAMPTZ DEFAULT NOW()
);

-- Leverage Positions
CREATE TABLE IF NOT EXISTS leverage_positions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_address TEXT NOT NULL,
    protocol TEXT NOT NULL,
    initial_deposit DECIMAL NOT NULL,
    current_collateral DECIMAL NOT NULL,
    current_debt DECIMAL NOT NULL,
    leverage DECIMAL NOT NULL,
    health_factor DECIMAL,
    loop_count INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_address, protocol)
);

-- Agent Configs
CREATE TABLE IF NOT EXISTS agent_configs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_address TEXT NOT NULL UNIQUE,
    config JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Harvests
CREATE TABLE IF NOT EXISTS harvests (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_address TEXT NOT NULL,
    executor_address TEXT NOT NULL,
    protocol TEXT NOT NULL,
    harvested_amount DECIMAL NOT NULL,
    executor_reward DECIMAL NOT NULL,
    tx_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_positions_user ON positions(user_address);
CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_address);
CREATE INDEX IF NOT EXISTS idx_leverage_user ON leverage_positions(user_address);
"""
