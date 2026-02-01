"""Check session key mismatch"""
import sys
sys.path.insert(0, '.')

from api.session_key_signer import derive_session_key, FACTORY_DEFAULT_SESSION_KEY
from api.agent_config_router import DEPLOYED_AGENTS

print("=== SESSION KEY CHECK ===")
print()

# Factory default
print(f"Factory default session key: {FACTORY_DEFAULT_SESSION_KEY}")
print()

# Get agent
for user_addr, user_agents in DEPLOYED_AGENTS.items():
    if isinstance(user_agents, list):
        for agent in user_agents:
            if agent.get('is_active'):
                agent_id = agent.get('id')
                user_address = agent.get('user_address')
                agent_address = agent.get('agent_address')
                
                print(f"Agent: {agent_id}")
                print(f"User: {user_address}")
                print(f"Smart Account: {agent_address}")
                print()
                
                try:
                    _, derived_addr = derive_session_key(agent_id, user_address)
                    print(f"Derived session key: {derived_addr}")
                    
                    if derived_addr.lower() == FACTORY_DEFAULT_SESSION_KEY.lower():
                        print("✅ MATCH!")
                    else:
                        print("❌ MISMATCH!")
                        print(f"  Expected: {FACTORY_DEFAULT_SESSION_KEY}")
                        print(f"  Got: {derived_addr}")
                except Exception as e:
                    print(f"Error: {e}")
                break
