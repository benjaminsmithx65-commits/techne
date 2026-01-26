"""Check which agents are actually used in the codebase"""
import os
import subprocess

agents_dir = 'agents'
files = [f for f in os.listdir(agents_dir) if f.endswith('.py') and f != '__init__.py' and f != '__pycache__']

print("=" * 60)
print("AGENT USAGE AUDIT")
print("=" * 60)

used = []
unused = []

for agent_file in sorted(files):
    name = agent_file.replace('.py', '')
    
    # Search for imports of this agent (excluding the agent's own file)
    search_patterns = [
        f'from agents.{name}',
        f'from .{name}',
        f'agents.{name}',
    ]
    
    count = 0
    for pattern in search_patterns:
        try:
            result = subprocess.run(
                ['findstr', '/s', '/i', '/c:' + pattern, '*.py'],
                capture_output=True, text=True, cwd='.'
            )
            # Count lines but exclude the agent's own file
            lines = [l for l in result.stdout.split('\n') if l and f'agents\\{agent_file}' not in l]
            count += len(lines)
        except:
            pass
    
    if count > 0:
        used.append((name, count))
        print(f"✅ {name}: {count} imports")
    else:
        unused.append(name)
        print(f"❌ {name}: NOT USED")

print("\n" + "=" * 60)
print(f"SUMMARY: {len(used)} USED / {len(unused)} UNUSED")
print("=" * 60)

if unused:
    print("\n⚠️ UNUSED AGENTS (can be removed):")
    for name in unused:
        print(f"  - agents/{name}.py")
