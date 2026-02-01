import requests
import json

# Check deployed agents
resp = requests.get('http://localhost:8000/api/deployed-agents', timeout=10)
agents = resp.json()

print('=== DEPLOYED AGENTS ===')
for agent in agents.get('agents', []):
    agent_id = agent.get('id', 'N/A')
    print(f"ID: {agent_id}")
    print(f"  Status: {agent.get('status')}")
    print(f"  User: {agent.get('user_address', 'N/A')}")
    print(f"  Agent Addr: {agent.get('agent_address', 'N/A')}")
    print(f"  Account Type: {agent.get('account_type')}")
    print()
