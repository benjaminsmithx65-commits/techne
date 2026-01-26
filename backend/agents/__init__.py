"""
Techne Protocol - Multi-Agent System
Artisan's Workshop of 9 Specialized Agents

Core Agents (MVP):
- Scout: Data collection (DeFiLlama, Beefy, whales)
- Appraiser: Risk analysis and verification
- Merchant: x402/Meridian payments
- Concierge: User-facing formatting
- Engineer: Execution layer (NEW!)

Extended Agents (Security & Optimization):
- Sentinel: Security monitoring, rug detection
- Historian: Historical data, trends, backtesting
- Arbitrageur: Yield optimization, rebalancing
- Guardian: Position monitoring, stop-loss, alerts

Infrastructure:
- Chainlink Oracle: Depeg monitoring (NEW!)
- Coordinator: Routes data between all agents
"""

# Core Agents
from artisan.scout_agent import scout_agent as scout, ScoutAgent
from .appraiser_agent import appraiser, AppraiserAgent, RiskLevel, VerificationStatus
from .merchant_agent import merchant, MerchantAgent, PaymentType, PaymentStatus
from .concierge_agent import concierge, ConciergeAgent

# NEW: Engineer Agent (Execution Layer)
from .engineer_agent import engineer, EngineerAgent, TaskType, TaskStatus

# Extended Agents
from .sentinel_agent import sentinel, SentinelAgent, ThreatLevel, SecurityFlag
from .historian_agent import historian, HistorianAgent
from .arbitrageur_agent import arbitrageur, ArbitrageurAgent
from .guardian_agent import guardian, GuardianAgent, AlertType, AlertSeverity
from .security_policy import security_policy, SecurityPolicyManager, ActionType, PolicyConstraints, SessionKey

# Infrastructure
from .chainlink_oracle import oracle as chainlink

# Coordinator - disabled due to legacy scout API
# from .coordinator import coordinator, AgentCoordinator
coordinator = None
AgentCoordinator = None

__all__ = [
    # Core singleton instances
    "scout",
    "appraiser", 
    "merchant",
    "concierge",
    "engineer",  # NEW
    
    # Extended singleton instances
    "sentinel",
    "historian",
    "arbitrageur",
    "guardian",
    
    # Infrastructure
    "chainlink",  # NEW
    
    # Coordinator
    "coordinator",
    
    # Core Classes
    "ScoutAgent",
    "AppraiserAgent",
    "MerchantAgent",
    "ConciergeAgent",
    "EngineerAgent",  # NEW
    
    # Extended Classes
    "SentinelAgent",
    "HistorianAgent",
    "ArbitrageurAgent",
    "GuardianAgent",
    "AgentCoordinator",
    
    # Enums
    "RiskLevel",
    "VerificationStatus",
    "PaymentType",
    "PaymentStatus",
    "ThreatLevel",
    "SecurityFlag",
    "AlertType",
    "AlertSeverity",
    "TaskType",  # NEW
    "TaskStatus",  # NEW
]


