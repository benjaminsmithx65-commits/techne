"""
Test Strategy Executor to see what it actually does with the deployed agent.
"""
import asyncio
import sys
sys.path.insert(0, '.')

async def test_executor():
    from agents.strategy_executor import StrategyExecutor
    from api.agent_config_router import DEPLOYED_AGENTS
    
    print("=== TEST STRATEGY EXECUTOR ===")
    print()
    
    # Check agents
    all_agents = []
    for user_addr, user_agents in DEPLOYED_AGENTS.items():
        print(f"User: {user_addr}")
        if isinstance(user_agents, list):
            for a in user_agents:
                print(f"  Agent: {a.get('id')}")
                print(f"    agent_address: {a.get('agent_address')}")
                print(f"    account_type: {a.get('account_type')}")
                print(f"    is_active: {a.get('is_active')}")
                if a.get('is_active'):
                    all_agents.append(a)
    
    print()
    print(f"Total active agents: {len(all_agents)}")
    
    if not all_agents:
        print("No active agents found!")
        return
    
    # Test execution
    executor = StrategyExecutor()
    agent = all_agents[0]
    
    print()
    print(f"=== Testing agent: {agent.get('id')} ===")
    print()
    
    # Test balance check
    user_address = agent.get('user_address')
    idle_balance = await executor.get_user_idle_balance(user_address, agent)
    print(f"Idle balance result: ${idle_balance:.2f}")
    
    # Test pool finding
    print()
    print("=== Finding pools ===")
    pools = await executor.find_matching_pools(agent)
    print(f"Found {len(pools)} pools")
    if pools:
        for p in pools[:3]:
            print(f"  {p.get('symbol')}: {p.get('apy')}% APY, ${p.get('tvl', 0):,.0f} TVL")
    
    print()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(test_executor())
