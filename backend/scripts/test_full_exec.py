"""Full test - trigger actual execution"""
import asyncio
import sys
sys.path.insert(0, '.')

async def test():
    from agents.strategy_executor import StrategyExecutor
    from api.agent_config_router import DEPLOYED_AGENTS
    
    executor = StrategyExecutor()
    
    print("=== SIMULATING FULL EXECUTION LOOP ===")
    print()
    
    # Get agents
    all_agents = []
    for user_agents in DEPLOYED_AGENTS.values():
        if isinstance(user_agents, list):
            all_agents.extend([a for a in user_agents if a.get("is_active", False)])
    
    print(f"Active agents: {len(all_agents)}")
    
    if not all_agents:
        print("No active agents!")
        return
    
    agent = all_agents[0]
    print(f"Testing: {agent.get('id')}")
    print()
    
    # Check compound timing
    should_compound = executor.check_should_compound(agent)
    print(f"Should compound: {should_compound}")
    print(f"  last_compound_time: {agent.get('last_compound_time')}")
    print(f"  compound_frequency: {agent.get('compound_frequency')}")
    
    if not should_compound:
        print("Skipping due to compound timing!")
        return
    
    print()
    print("=== Calling execute_agent_strategy ===")
    await executor.execute_agent_strategy(agent)
    print()
    print("Done!")

asyncio.run(test())
