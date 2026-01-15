"""
Audit Status Checker
Checks if protocols/contracts have been professionally audited.
Uses a database of known audits + De.Fi API fallback.
"""

import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Known protocol audits database (hardcoded for major protocols)
KNOWN_AUDITS = {
    # DEXes
    "aerodrome": {
        "audited": True,
        "auditors": ["OpenZeppelin", "Pashov Audit Group"],
        "score": 92,
        "date": "2023-08",
        "url": "https://docs.aerodrome.finance/security"
    },
    "velodrome": {
        "audited": True,
        "auditors": ["OpenZeppelin", "Code4rena"],
        "score": 90,
        "date": "2022-06",
        "url": "https://docs.velodrome.finance/security"
    },
    "uniswap-v2": {
        "audited": True,
        "auditors": ["OpenZeppelin", "Trail of Bits", "Consensys Diligence"],
        "score": 98,
        "date": "2020-03",
        "url": "https://docs.uniswap.org/contracts/v2/overview"
    },
    "uniswap-v3": {
        "audited": True,
        "auditors": ["ABDK", "Trail of Bits", "samczsun"],
        "score": 97,
        "date": "2021-05",
        "url": "https://docs.uniswap.org/contracts/v3/overview"
    },
    "sushiswap": {
        "audited": True,
        "auditors": ["Quantstamp", "Peckshield"],
        "score": 85,
        "date": "2020-09",
        "url": "https://docs.sushi.com/docs/Developers/Security"
    },
    "curve": {
        "audited": True,
        "auditors": ["Trail of Bits", "Quantstamp", "MixBytes"],
        "score": 94,
        "date": "2020-01",
        "url": "https://docs.curve.fi/security"
    },
    "pancakeswap": {
        "audited": True,
        "auditors": ["CertiK", "SlowMist", "Peckshield"],
        "score": 91,
        "date": "2021-04",
        "url": "https://docs.pancakeswap.finance/products/security"
    },
    "camelot": {
        "audited": True,
        "auditors": ["Paladin", "Pashov"],
        "score": 88,
        "date": "2022-12",
        "url": "https://docs.camelot.exchange/security"
    },
    "trader-joe": {
        "audited": True,
        "auditors": ["Omniscia", "Guardian Audits"],
        "score": 87,
        "date": "2023-01",
        "url": "https://docs.traderjoexyz.com/security"
    },
    
    # Lending
    "aave-v2": {
        "audited": True,
        "auditors": ["OpenZeppelin", "Trail of Bits", "Consensys Diligence", "CertiK"],
        "score": 98,
        "date": "2020-12",
        "url": "https://docs.aave.com/developers/security-and-audits"
    },
    "aave-v3": {
        "audited": True,
        "auditors": ["OpenZeppelin", "Trail of Bits", "Peckshield", "SigmaPrime"],
        "score": 97,
        "date": "2022-03",
        "url": "https://docs.aave.com/developers/security-and-audits"
    },
    "compound": {
        "audited": True,
        "auditors": ["OpenZeppelin", "Trail of Bits"],
        "score": 96,
        "date": "2019-08",
        "url": "https://docs.compound.finance/security"
    },
    "morpho": {
        "audited": True,
        "auditors": ["Cantina", "Spearbit", "Trail of Bits"],
        "score": 93,
        "date": "2024-01",
        "url": "https://docs.morpho.xyz/security"
    },
    
    # Solana
    "raydium": {
        "audited": True,
        "auditors": ["Kudelski Security", "SlowMist"],
        "score": 86,
        "date": "2021-05",
        "url": "https://docs.raydium.io/raydium/security"
    },
    "orca": {
        "audited": True,
        "auditors": ["Kudelski Security", "Neodyme"],
        "score": 89,
        "date": "2022-03",
        "url": "https://docs.orca.so/security"
    },
    "meteora": {
        "audited": True,
        "auditors": ["OtterSec", "MadShield"],
        "score": 85,
        "date": "2023-09",
        "url": "https://docs.meteora.ag/security"
    },
    "jupiter": {
        "audited": True,
        "auditors": ["OtterSec"],
        "score": 88,
        "date": "2023-06",
        "url": "https://station.jup.ag/docs/security"
    },
    
    # Liquid Staking
    "lido": {
        "audited": True,
        "auditors": ["Sigma Prime", "Quantstamp", "MixBytes", "StateMind"],
        "score": 96,
        "date": "2020-12",
        "url": "https://docs.lido.fi/security/audits"
    },
    "rocket-pool": {
        "audited": True,
        "auditors": ["Sigma Prime", "Trail of Bits", "Consensys Diligence"],
        "score": 95,
        "date": "2021-10",
        "url": "https://docs.rocketpool.net/overview/security"
    },
    
    # Yield Aggregators
    "beefy": {
        "audited": True,
        "auditors": ["CertiK", "Quantstamp"],
        "score": 88,
        "date": "2021-07",
        "url": "https://docs.beefy.finance/safety"
    },
    "yearn": {
        "audited": True,
        "auditors": ["Trail of Bits", "Mixbytes", "Decurity"],
        "score": 92,
        "date": "2020-09",
        "url": "https://docs.yearn.fi/security"
    },
}

# Protocol name normalization
PROTOCOL_ALIASES = {
    "uniswap": "uniswap-v3",
    "univ3": "uniswap-v3",
    "univ2": "uniswap-v2",
    "aave": "aave-v3",
    "comp": "compound",
    "sushi": "sushiswap",
    "joe": "trader-joe",
    "traderjoe": "trader-joe",
    "rocketpool": "rocket-pool",
    # Chain-specific variants
    "aerodrome-base": "aerodrome",
    "aerodrome-v1": "aerodrome",
    "aerodrome-v2": "aerodrome",
    "aerodrome-v3": "aerodrome",
    "aerodrome-slipstream": "aerodrome",
    "velodrome-optimism": "velodrome",
    "velodrome-v2": "velodrome",
    "uniswap-v3-base": "uniswap-v3",
    "uniswap-v3-arbitrum": "uniswap-v3",
    "uniswap-v3-polygon": "uniswap-v3",
    "sushiswap-arbitrum": "sushiswap",
    "camelot-v2": "camelot",
    "camelot-v3": "camelot",
}


class AuditChecker:
    """Check audit status for protocols and contracts."""
    
    def __init__(self):
        self.cache = {}
        self.defi_api_base = "https://api.de.fi/v1"
    
    def normalize_protocol_name(self, name: str) -> str:
        """Normalize protocol name for lookup."""
        # Basic normalization
        normalized = name.lower().strip().replace(" ", "-").replace("_", "-")
        
        # Remove common chain suffixes
        chain_suffixes = ["-base", "-ethereum", "-arbitrum", "-optimism", "-polygon", "-bsc", "-avalanche", "-solana"]
        for suffix in chain_suffixes:
            if normalized.endswith(suffix):
                base_name = normalized[:-len(suffix)]
                # Check if base name exists in known audits
                if base_name in KNOWN_AUDITS:
                    return base_name
        
        # Check aliases
        return PROTOCOL_ALIASES.get(normalized, normalized)
    
    async def check_audit_status(
        self,
        protocol_name: str,
        contract_address: Optional[str] = None,
        chain: str = "base"
    ) -> Dict[str, Any]:
        """
        Check if a protocol/contract has been audited.
        
        Returns:
            {
                "audited": bool,
                "auditors": ["OpenZeppelin", "Trail of Bits"],
                "score": 92,
                "date": "2023-08",
                "url": "https://...",
                "source": "known_db" | "defi_api" | "unknown"
            }
        """
        # Normalize protocol name
        normalized = self.normalize_protocol_name(protocol_name)
        
        # Check known database first
        if normalized in KNOWN_AUDITS:
            result = KNOWN_AUDITS[normalized].copy()
            result["source"] = "known_db"
            result["protocol"] = protocol_name
            return result
        
        # Try De.Fi API if contract address provided
        if contract_address:
            try:
                defi_result = await self._check_defi_api(contract_address, chain)
                if defi_result:
                    return defi_result
            except Exception as e:
                logger.warning(f"De.Fi API check failed: {e}")
        
        # Unknown protocol
        return {
            "audited": False,
            "auditors": [],
            "score": 0,
            "date": None,
            "url": None,
            "source": "unknown",
            "protocol": protocol_name,
            "note": "No audit information found. Exercise caution."
        }
    
    async def _check_defi_api(
        self, 
        contract_address: str, 
        chain: str
    ) -> Optional[Dict[str, Any]]:
        """Check De.Fi API for contract security info."""
        # De.Fi scanner API (free tier)
        chain_map = {
            "base": "base",
            "ethereum": "eth",
            "arbitrum": "arb",
            "optimism": "op",
            "polygon": "polygon",
            "bsc": "bsc"
        }
        
        defi_chain = chain_map.get(chain.lower(), chain.lower())
        url = f"https://api.de.fi/v1/security/{defi_chain}/{contract_address}"
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse De.Fi response
                if data.get("audits"):
                    audits = data["audits"]
                    return {
                        "audited": True,
                        "auditors": [a.get("auditor", "Unknown") for a in audits],
                        "score": data.get("score", 0),
                        "date": audits[0].get("date") if audits else None,
                        "url": data.get("report_url"),
                        "source": "defi_api",
                        "issues": {
                            "critical": data.get("critical_issues", 0),
                            "high": data.get("high_issues", 0),
                            "medium": data.get("medium_issues", 0)
                        }
                    }
        
        return None
    
    def get_audit_badge_html(self, audit_result: Dict[str, Any]) -> str:
        """Generate HTML badge for audit status."""
        if audit_result.get("audited"):
            score = audit_result.get("score", 0)
            if score >= 90:
                color = "#10B981"
                label = "Excellent"
            elif score >= 75:
                color = "#3B82F6"
                label = "Good"
            elif score >= 50:
                color = "#FBBF24"
                label = "Fair"
            else:
                color = "#EF4444"
                label = "Low"
            
            auditors = ", ".join(audit_result.get("auditors", [])[:2])
            return f"""
                <div class="audit-badge audited" style="--badge-color: {color}">
                    <span class="audit-icon">✅</span>
                    <span class="audit-text">Audited by {auditors}</span>
                    <span class="audit-score">{score}/100</span>
                </div>
            """
        else:
            return """
                <div class="audit-badge not-audited">
                    <span class="audit-icon">⚠️</span>
                    <span class="audit-text">No verified audit</span>
                </div>
            """


# Singleton instance
audit_checker = AuditChecker()
