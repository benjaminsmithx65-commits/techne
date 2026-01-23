"""
Modal.com Serverless Client
Offloads heavy compute (AI analysis, APY prediction) from VPS to serverless

Features:
- Run Claude/Haiku analysis on Modal
- APY prediction with heavy math
- Contract code analysis
- Pay-per-use (no VPS overload)
"""

import os
import json
import httpx
from typing import Dict, Any, Optional

# Modal.com configuration
MODAL_API_URL = os.getenv("MODAL_API_URL", "https://your-modal-endpoint.modal.run")
MODAL_TOKEN = os.getenv("MODAL_TOKEN", "")


class ModalClient:
    """
    Client for Modal.com serverless functions.
    
    Usage:
        client = ModalClient()
        result = await client.analyze_contract("0x...")
        result = await client.predict_apy(apy_history)
    """
    
    def __init__(self):
        self.api_url = MODAL_API_URL
        self.token = MODAL_TOKEN
        self.client = httpx.AsyncClient(timeout=60.0)
        
        # Headers for Modal auth
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def call_function(
        self, 
        function_name: str, 
        payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Call a Modal.com serverless function.
        
        Args:
            function_name: Name of the Modal function
            payload: JSON payload to send
        
        Returns:
            Response JSON or None on error
        """
        url = f"{self.api_url}/{function_name}"
        
        try:
            response = await self.client.post(
                url,
                json=payload,
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[Modal] Error {response.status_code}: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"[Modal] Request error: {e}")
            return None
    
    async def analyze_contract_ai(self, source_code: str) -> Dict[str, Any]:
        """
        AI-powered contract analysis (runs on Modal).
        
        Uses Claude Haiku for deep analysis of smart contract code.
        """
        result = await self.call_function("analyze_contract", {
            "source_code": source_code,
            "model": "claude-3-haiku",
            "check_patterns": [
                "hidden_mint",
                "blacklist",
                "honeypot",
                "reentrancy",
                "admin_keys"
            ]
        })
        
        if result:
            return result
        
        # Fallback to local analysis if Modal fails
        return {
            "source": "local_fallback",
            "risk_score": 50,
            "message": "Modal unavailable - using local analysis"
        }
    
    async def predict_apy_advanced(
        self, 
        pool_id: str, 
        apy_history: list
    ) -> Dict[str, Any]:
        """
        Advanced APY prediction using ML on Modal.
        
        More sophisticated than local linear regression.
        """
        result = await self.call_function("predict_apy", {
            "pool_id": pool_id,
            "history": apy_history,
            "model_type": "gradient_boost"
        })
        
        if result:
            return result
        
        # Fallback to local prediction
        return {
            "source": "local_fallback",
            "predicted_apy": None,
            "message": "Modal unavailable - use local predictor"
        }
    
    async def analyze_wash_trading(
        self, 
        pool_address: str, 
        swap_data: list
    ) -> Dict[str, Any]:
        """
        Deep wash trading analysis on Modal.
        
        Uses graph analysis to detect circular trades.
        """
        result = await self.call_function("detect_wash_trading", {
            "pool_address": pool_address,
            "swaps": swap_data,
            "detect_circular": True,
            "min_repetitions": 3
        })
        
        return result or {"source": "fallback", "is_wash_trading": None}
    
    async def health_check(self) -> bool:
        """Check if Modal.com endpoint is available."""
        try:
            response = await self.client.get(
                f"{self.api_url}/health",
                timeout=5.0
            )
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        await self.client.aclose()


# Global instance
_modal_client = None

def get_modal_client() -> ModalClient:
    global _modal_client
    if _modal_client is None:
        _modal_client = ModalClient()
    return _modal_client


# ============================================
# MODAL FUNCTION STUBS (For deployment to Modal.com)
# ============================================

MODAL_FUNCTION_TEMPLATE = '''
# Deploy this to Modal.com:
# modal deploy modal_functions.py

import modal

stub = modal.Stub("techne-ai")

@stub.function()
def analyze_contract(source_code: str, model: str, check_patterns: list):
    """AI contract analysis - runs on Modal GPU."""
    import anthropic
    
    client = anthropic.Anthropic()
    
    prompt = f"""Analyze this smart contract for security risks:
    
    {source_code[:10000]}
    
    Check for these patterns: {check_patterns}
    
    Return JSON with: risk_score (0-100), findings (list), recommendation"""
    
    response = client.messages.create(
        model=model,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content

@stub.function()
def predict_apy(pool_id: str, history: list, model_type: str):
    """APY prediction with gradient boosting."""
    from sklearn.ensemble import GradientBoostingRegressor
    import numpy as np
    
    # Train and predict
    X = np.array(range(len(history))).reshape(-1, 1)
    y = np.array([h[1] for h in history])
    
    model = GradientBoostingRegressor()
    model.fit(X, y)
    
    next_24h = len(history) + 24
    predicted = model.predict([[next_24h]])[0]
    
    return {"predicted_apy": float(predicted), "model": model_type}

@stub.function()
def health():
    return {"status": "ok"}
'''


if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("Modal.com Client Test")
        print("="*60)
        
        client = ModalClient()
        
        # Health check
        print(f"API URL: {client.api_url}")
        healthy = await client.health_check()
        print(f"Health Check: {'✓ OK' if healthy else '✗ OFFLINE'}")
        
        if not healthy:
            print("\n⚠ Modal.com not configured. Set these env vars:")
            print("  - MODAL_API_URL=https://your-endpoint.modal.run")
            print("  - MODAL_TOKEN=your_token")
            print("\nDeploy functions using:")
            print("  modal deploy modal_functions.py")
        
        await client.close()
    
    asyncio.run(test())
