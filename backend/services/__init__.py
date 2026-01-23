"""
Advanced Agent V2 Services
Real-time detection, AI analysis, and predictive models
"""

from .price_oracle import PythOracle, get_oracle, is_price_stale
from .pool_discovery import PoolDiscovery, get_discovery
from .scam_detector import ScamDetector, get_detector
from .wash_detector import WashTradingDetector, get_wash_detector
from .il_predictor import ILDivergencePredictor, get_il_predictor
from .apy_predictor import APYPredictor, get_apy_predictor

__all__ = [
    # Price Oracle
    "PythOracle",
    "get_oracle",
    "is_price_stale",
    
    # Pool Discovery
    "PoolDiscovery",
    "get_discovery",
    
    # Scam Detection
    "ScamDetector",
    "get_detector",
    
    # Wash Trading
    "WashTradingDetector",
    "get_wash_detector",
    
    # IL Prediction
    "ILDivergencePredictor",
    "get_il_predictor",
    
    # APY Prediction
    "APYPredictor",
    "get_apy_predictor",
]
