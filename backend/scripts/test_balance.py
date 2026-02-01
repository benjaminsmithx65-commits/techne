"""Test balance check only"""
import asyncio
import sys
sys.path.insert(0, '.')

async def test():
    from agents.strategy_executor import StrategyExecutor
    from api.agent_config_router import DEPLOYED_AGENTS
    
    executor = StrategyExecutor()
    
    # Get first agent
    for user_addr, user_agents in DEPLOYED_AGENTS.items():
        if isinstance(user_agents, list):
            for a in user_agents:
                if a.get('is_active'):
                    agent = a
                    print(f"Agent: {agent.get('id')}")
                    print(f"User address: {agent.get('user_address')}")
                    print(f"Agent address: {agent.get('agent_address')}")
                    print()
                    
                    try:
                        idle_balance = await executor.get_user_idle_balance(
                            agent.get('user_address'),
                            agent
                        )
                        print(f"RESULT: ${idle_balance:.2f}")
                    except Exception as e:
                        print(f"ERROR: {e}")
                        import traceback
                        traceback.print_exc()
                    return

asyncio.run(test())
