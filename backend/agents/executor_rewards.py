"""
Executor Rewards System
Based on Revert Finance Compoundor pattern.

Allows public harvesting with reward for executor who pays gas.
"""

from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class RewardConversion(Enum):
    """How to pay rewards (from Compoundor)"""
    NONE = "none"           # Split between token0/token1
    TOKEN_0 = "token_0"     # All in token0
    TOKEN_1 = "token_1"     # All in token1


@dataclass
class HarvestReward:
    """Reward for executing harvest"""
    executor: str
    user: str
    protocol: str
    harvested_amount: float  # Total harvested
    reward_amount: float     # Executor reward
    reward_token: str
    tx_hash: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class ExecutorRewards:
    """
    Manages executor rewards for public harvesting.
    
    Inspired by Revert Finance:
    - 2% total reward (split protocol/executor)
    - 1% goes to executor who triggers harvest
    - 1% goes to protocol treasury
    """
    
    # Reward percentages (in basis points, 100 = 1%)
    TOTAL_REWARD_BPS = 200   # 2% total
    EXECUTOR_REWARD_BPS = 100  # 1% to executor
    PROTOCOL_REWARD_BPS = 100  # 1% to protocol
    
    def __init__(self):
        self.pending_rewards: Dict[str, float] = {}  # executor -> amount
        self.protocol_rewards: Dict[str, float] = {}  # protocol -> amount
        self.reward_history: list = []
    
    def calculate_rewards(
        self, 
        harvested_amount: float,
        executor: str,
        user: str,
        protocol: str
    ) -> HarvestReward:
        """
        Calculate executor reward for harvesting.
        
        Returns HarvestReward with breakdown.
        """
        # Skip reward if executor is the position owner
        if executor.lower() == user.lower():
            return HarvestReward(
                executor=executor,
                user=user,
                protocol=protocol,
                harvested_amount=harvested_amount,
                reward_amount=0,
                reward_token="USDC"
            )
        
        # Calculate rewards
        total_reward = harvested_amount * self.TOTAL_REWARD_BPS / 10000
        executor_reward = harvested_amount * self.EXECUTOR_REWARD_BPS / 10000
        protocol_reward = harvested_amount * self.PROTOCOL_REWARD_BPS / 10000
        
        # Track rewards
        self.pending_rewards[executor] = self.pending_rewards.get(executor, 0) + executor_reward
        self.protocol_rewards[protocol] = self.protocol_rewards.get(protocol, 0) + protocol_reward
        
        reward = HarvestReward(
            executor=executor,
            user=user,
            protocol=protocol,
            harvested_amount=harvested_amount,
            reward_amount=executor_reward,
            reward_token="USDC"
        )
        
        self.reward_history.append(reward)
        
        print(f"[ExecutorRewards] Harvest reward: ${executor_reward:.4f} to {executor[:10]}...")
        print(f"[ExecutorRewards] Protocol fee: ${protocol_reward:.4f}")
        
        return reward
    
    def get_pending_rewards(self, executor: str) -> float:
        """Get pending rewards for executor"""
        return self.pending_rewards.get(executor, 0)
    
    def claim_rewards(self, executor: str) -> float:
        """Claim pending rewards (marks as claimed)"""
        amount = self.pending_rewards.pop(executor, 0)
        if amount > 0:
            print(f"[ExecutorRewards] Claimed ${amount:.4f} for {executor[:10]}...")
        return amount
    
    def get_stats(self) -> dict:
        """Get reward system stats"""
        total_executor_rewards = sum(self.pending_rewards.values())
        total_protocol_rewards = sum(self.protocol_rewards.values())
        
        return {
            "total_harvests": len(self.reward_history),
            "pending_executor_rewards": total_executor_rewards,
            "total_protocol_rewards": total_protocol_rewards,
            "active_executors": len(self.pending_rewards)
        }


# Global instance
executor_rewards = ExecutorRewards()


def public_harvest_endpoint():
    """
    Example of how to expose public harvesting.
    Anyone can call this to trigger harvest and earn reward.
    """
    # This would be exposed as an API endpoint:
    # POST /api/harvest/execute
    # {
    #   "user": "0x...",
    #   "protocol": "aave"
    # }
    # 
    # Executor (msg.sender) earns 1% of harvested yield
    pass
