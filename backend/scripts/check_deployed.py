from api.agent_config_router import DEPLOYED_AGENTS

print('=== CHECKING DEPLOYED AGENTS ===')
all_agents = []
for user_addr, user_agents in DEPLOYED_AGENTS.items():
    print(f'User: {user_addr}')
    if isinstance(user_agents, list):
        for a in user_agents:
            agent_id = a.get('id', 'N/A')
            print(f'  Agent ID: {agent_id}')
            print(f'    is_active: {a.get("is_active")}')
            print(f'    agent_address: {a.get("agent_address")}')
            print(f'    account_type: {a.get("account_type")}')
            if a.get('is_active'):
                all_agents.append(a)
    elif isinstance(user_agents, dict):
        print('  (dict format)')
        if user_agents.get('is_active'):
            all_agents.append(user_agents)

print()
print(f'Total active agents found: {len(all_agents)}')
