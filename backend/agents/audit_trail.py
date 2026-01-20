"""
Audit Trail System
Logs all agent actions, transactions, and decisions
Supports CSV export for tax reporting
"""

import os
import json
import csv
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path


class ActionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    SWAP = "swap"
    ENTER_LP = "enter_lp"
    EXIT_LP = "exit_lp"
    REBALANCE = "rebalance"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    AGENT_DEPLOY = "agent_deploy"
    AGENT_PAUSE = "agent_pause"
    POOL_DISCOVERY = "pool_discovery"
    RISK_ALERT = "risk_alert"
    EMERGENCY_EXIT = "emergency_exit"  # Triggered by max_drawdown


@dataclass
class AuditEntry:
    """Single audit log entry"""
    timestamp: str
    action_type: str
    agent_id: str
    wallet_address: str
    details: Dict[str, Any]
    tx_hash: Optional[str] = None
    gas_used: Optional[int] = None
    value_usd: Optional[float] = None
    success: bool = True
    error: Optional[str] = None


class AuditTrail:
    """
    Comprehensive audit logging for agent operations
    
    Features:
    - JSON file storage
    - CSV export for tax reporting
    - Per-agent filtering
    - Date range queries
    """
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "audit")
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.data_dir / "audit_log.json"
        self.entries: List[AuditEntry] = []
        
        # Load existing entries
        self._load()
    
    def _load(self):
        """Load existing audit entries from file"""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
                    self.entries = [
                        AuditEntry(**entry) for entry in data
                    ]
            except Exception as e:
                print(f"[AuditTrail] Error loading: {e}")
                self.entries = []
    
    def _save(self):
        """Save audit entries to file"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump([asdict(e) for e in self.entries], f, indent=2)
        except Exception as e:
            print(f"[AuditTrail] Error saving: {e}")
    
    def log(
        self,
        action_type: ActionType,
        agent_id: str,
        wallet_address: str,
        details: Dict[str, Any],
        tx_hash: str = None,
        gas_used: int = None,
        value_usd: float = None,
        success: bool = True,
        error: str = None
    ) -> AuditEntry:
        """Log an action to the audit trail"""
        entry = AuditEntry(
            timestamp=datetime.utcnow().isoformat(),
            action_type=action_type.value,
            agent_id=agent_id,
            wallet_address=wallet_address,
            details=details,
            tx_hash=tx_hash,
            gas_used=gas_used,
            value_usd=value_usd,
            success=success,
            error=error
        )
        
        self.entries.append(entry)
        self._save()
        
        print(f"[AuditTrail] {action_type.value}: {agent_id[:8]}... | ${value_usd or 0:.2f}")
        
        return entry
    
    def log_deposit(self, agent_id: str, wallet: str, amount: float, tx_hash: str = None):
        """Log a deposit action"""
        return self.log(
            ActionType.DEPOSIT,
            agent_id,
            wallet,
            {"amount_usdc": amount},
            tx_hash=tx_hash,
            value_usd=amount
        )
    
    def log_swap(self, agent_id: str, wallet: str, from_token: str, to_token: str, 
                 amount: float, tx_hash: str = None):
        """Log a token swap"""
        return self.log(
            ActionType.SWAP,
            agent_id,
            wallet,
            {"from": from_token, "to": to_token, "amount": amount},
            tx_hash=tx_hash,
            value_usd=amount
        )
    
    def log_lp_entry(self, agent_id: str, wallet: str, pool: str, amount: float, tx_hash: str = None):
        """Log LP position entry"""
        return self.log(
            ActionType.ENTER_LP,
            agent_id,
            wallet,
            {"pool": pool, "amount_usdc": amount},
            tx_hash=tx_hash,
            value_usd=amount
        )
    
    def log_stop_loss(self, agent_id: str, wallet: str, pool: str, loss_percent: float, exit_value: float):
        """Log stop-loss trigger"""
        return self.log(
            ActionType.STOP_LOSS,
            agent_id,
            wallet,
            {"pool": pool, "loss_percent": loss_percent, "exit_value": exit_value},
            value_usd=exit_value
        )
    
    def log_risk_alert(self, agent_id: str, wallet: str, alert_type: str, message: str):
        """Log a risk alert"""
        return self.log(
            ActionType.RISK_ALERT,
            agent_id,
            wallet,
            {"alert_type": alert_type, "message": message}
        )
    
    def get_entries(
        self,
        agent_id: str = None,
        wallet_address: str = None,
        action_type: ActionType = None,
        start_date: str = None,
        end_date: str = None
    ) -> List[AuditEntry]:
        """Query audit entries with filters"""
        results = self.entries
        
        if agent_id:
            results = [e for e in results if e.agent_id == agent_id]
        
        if wallet_address:
            results = [e for e in results if e.wallet_address == wallet_address]
        
        if action_type:
            results = [e for e in results if e.action_type == action_type.value]
        
        if start_date:
            results = [e for e in results if e.timestamp >= start_date]
        
        if end_date:
            results = [e for e in results if e.timestamp <= end_date]
        
        return results
    
    def get_summary(self, agent_id: str = None) -> Dict:
        """Get summary statistics"""
        entries = self.get_entries(agent_id=agent_id)
        
        total_deposits = sum(
            e.value_usd or 0 for e in entries 
            if e.action_type == ActionType.DEPOSIT.value
        )
        total_withdrawals = sum(
            e.value_usd or 0 for e in entries 
            if e.action_type == ActionType.WITHDRAW.value
        )
        total_swaps = len([e for e in entries if e.action_type == ActionType.SWAP.value])
        total_lp_entries = len([e for e in entries if e.action_type == ActionType.ENTER_LP.value])
        stop_losses = len([e for e in entries if e.action_type == ActionType.STOP_LOSS.value])
        
        return {
            "total_entries": len(entries),
            "total_deposits_usd": total_deposits,
            "total_withdrawals_usd": total_withdrawals,
            "net_flow_usd": total_deposits - total_withdrawals,
            "total_swaps": total_swaps,
            "total_lp_entries": total_lp_entries,
            "stop_losses_triggered": stop_losses
        }
    
    def export_csv(self, filepath: str = None, agent_id: str = None) -> str:
        """Export audit trail to CSV for tax reporting"""
        if filepath is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filepath = self.data_dir / f"audit_export_{timestamp}.csv"
        
        entries = self.get_entries(agent_id=agent_id)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "Timestamp", "Action", "Agent ID", "Wallet", 
                "TX Hash", "Value (USD)", "Gas Used", "Success", "Details"
            ])
            
            # Data rows
            for e in entries:
                writer.writerow([
                    e.timestamp,
                    e.action_type,
                    e.agent_id,
                    e.wallet_address,
                    e.tx_hash or "",
                    e.value_usd or "",
                    e.gas_used or "",
                    "Yes" if e.success else "No",
                    json.dumps(e.details)
                ])
        
        print(f"[AuditTrail] Exported {len(entries)} entries to {filepath}")
        return str(filepath)


# Global instance
audit_trail = AuditTrail()


# Convenience functions
def log_deposit(agent_id: str, wallet: str, amount: float, tx_hash: str = None):
    return audit_trail.log_deposit(agent_id, wallet, amount, tx_hash)

def log_swap(agent_id: str, wallet: str, from_token: str, to_token: str, amount: float, tx_hash: str = None):
    return audit_trail.log_swap(agent_id, wallet, from_token, to_token, amount, tx_hash)

def log_lp_entry(agent_id: str, wallet: str, pool: str, amount: float, tx_hash: str = None):
    return audit_trail.log_lp_entry(agent_id, wallet, pool, amount, tx_hash)

def export_csv(filepath: str = None, agent_id: str = None) -> str:
    return audit_trail.export_csv(filepath, agent_id)
