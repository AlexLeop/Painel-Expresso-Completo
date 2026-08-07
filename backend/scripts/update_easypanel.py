import json
import os

filepath = r"c:\Users\lxleo\Documents\Expresso Neves\Painel Expresso Neves e Django DRF\easypanel-template.json"

with open(filepath, 'r', encoding='utf-8') as f:
    data = json.load(f)

supabase_envs = [
    "SUPABASE_URL=${SUPABASE_URL:-https://xxxx.supabase.co}",
    "SUPABASE_KEY=${SUPABASE_KEY:-sua-chave-anon}",
    "SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET:-super-secret-jwt-token-with-at-least-32-characters-long}"
]

for service in data.get('services', []):
    if service.get('type') == 'app' and service['data'].get('serviceName') in ['django', 'fastapi', 'celery_worker', 'celery_beat']:
        env_str = service['data'].get('env', '')
        lines = env_str.split('\n')
        # Remove any empty lines
        lines = [line for line in lines if line.strip()]
        
        # Check if already has SUPABASE_URL
        if any('SUPABASE_URL' in line for line in lines):
            continue
            
        # Add new env vars.
        # Format is index=VALUE, but wait, Easypanel envs are just strings separated by \n where each line is KEY=VALUE, or sometimes i=KEY=VALUE?
        # Looking at original: "0=DATABASE_URL=... \n 1=DIRECT_URL=..."
        # We can just extract the indices, find max index, and append.
        
        new_lines = []
        max_idx = -1
        for line in lines:
            if '=' in line:
                idx_part = line.split('=')[0]
                if idx_part.isdigit():
                    max_idx = max(max_idx, int(idx_part))
        
        for env in supabase_envs:
            max_idx += 1
            lines.insert(0, f"{max_idx}={env}")
            
        # Fix the indices to be sequential
        fixed_lines = []
        for i, line in enumerate(lines):
            # remove old index prefix if exists
            if '=' in line:
                parts = line.split('=', 1)
                if parts[0].isdigit():
                    line = parts[1]
            fixed_lines.append(f"{i}={line}")
            
        service['data']['env'] = '\n'.join(fixed_lines)

with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False) # remove indentation so it stays 1 line if that's how it was
