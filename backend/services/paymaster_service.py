"""
Pimlico Paymaster Service for ERC-4337

Handles gas sponsorship for UserOperations via Pimlico's Verifying Paymaster.
This enables gasless transactions for users through Smart Accounts.
"""

import os
import aiohttp
from typing import Optional, Dict, Any
from web3 import Web3

# Configuration
PIMLICO_API_KEY = os.getenv("PIMLICO_API_KEY", "")
PIMLICO_BUNDLER_URL = os.getenv("PIMLICO_BUNDLER_URL", "")
CHAIN_ID = 8453  # Base mainnet

# EntryPoint v0.7
ENTRYPOINT_V07 = "0x0000000071727De22E5E9d8BAf0edAc6f37da032"


class PimlicoPaymasterService:
    """
    Paymaster service using Pimlico's sponsorship API.
    
    Pimlico offers:
    - pm_sponsorUserOperation: Sponsor gas for a UserOp
    - pm_validateSponsorshipPolicies: Check if user can be sponsored
    """
    
    def __init__(self):
        self.bundler_url = PIMLICO_BUNDLER_URL
        self.api_key = PIMLICO_API_KEY
        
        if not self.bundler_url:
            print("[Paymaster] WARNING: PIMLICO_BUNDLER_URL not set")
    
    async def sponsor_user_operation(
        self,
        user_op: Dict[str, Any],
        sender: str
    ) -> Optional[str]:
        """
        Sponsor a UserOperation via Pimlico.
        
        Args:
            user_op: The UserOperation to sponsor
            sender: Smart Account address
            
        Returns:
            paymasterAndData string to include in UserOp, or None if sponsorship denied
        """
        if not self.bundler_url:
            print("[Paymaster] Cannot sponsor - bundler URL not configured")
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                # Use Pimlico's sponsorship API
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "pm_sponsorUserOperation",
                    "params": [
                        {
                            "sender": sender,
                            "nonce": user_op.get("nonce", "0x0"),
                            "callData": user_op.get("callData", "0x"),
                            "callGasLimit": user_op.get("callGasLimit", "0x50000"),
                            "verificationGasLimit": user_op.get("verificationGasLimit", "0x20000"),
                            "preVerificationGas": user_op.get("preVerificationGas", "0x10000"),
                            "maxFeePerGas": user_op.get("maxFeePerGas", "0x1"),
                            "maxPriorityFeePerGas": user_op.get("maxPriorityFeePerGas", "0x1"),
                            "signature": "0x" + "00" * 65  # Dummy signature for estimation
                        },
                        ENTRYPOINT_V07
                    ]
                }
                
                async with session.post(self.bundler_url, json=payload) as resp:
                    result = await resp.json()
                    
                    if "error" in result:
                        print(f"[Paymaster] Sponsorship denied: {result['error']}")
                        return None
                    
                    sponsor_result = result.get("result", {})
                    paymaster_and_data = sponsor_result.get("paymasterAndData", "0x")
                    
                    print(f"[Paymaster] Sponsored! paymasterAndData={paymaster_and_data[:50]}...")
                    return paymaster_and_data
                    
        except Exception as e:
            print(f"[Paymaster] Sponsorship error: {e}")
            return None
    
    async def get_gas_estimates(
        self,
        user_op: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Get gas estimates from bundler.
        
        Returns dict with:
            - callGasLimit
            - verificationGasLimit
            - preVerificationGas
        """
        if not self.bundler_url:
            return {
                "callGasLimit": "0x50000",
                "verificationGasLimit": "0x20000",
                "preVerificationGas": "0x10000"
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_estimateUserOperationGas",
                    "params": [user_op, ENTRYPOINT_V07]
                }
                
                async with session.post(self.bundler_url, json=payload) as resp:
                    result = await resp.json()
                    
                    if "error" in result:
                        print(f"[Paymaster] Gas estimation failed: {result['error']}")
                        return {
                            "callGasLimit": "0x50000",
                            "verificationGasLimit": "0x20000",
                            "preVerificationGas": "0x10000"
                        }
                    
                    return result.get("result", {})
                    
        except Exception as e:
            print(f"[Paymaster] Gas estimation error: {e}")
            return {
                "callGasLimit": "0x50000",
                "verificationGasLimit": "0x20000",
                "preVerificationGas": "0x10000"
            }


# Singleton
_paymaster_service = None

def get_paymaster_service() -> PimlicoPaymasterService:
    global _paymaster_service
    if _paymaster_service is None:
        _paymaster_service = PimlicoPaymasterService()
    return _paymaster_service
