import os
import re

file_path = "integration/tasks.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the webhook dispatch in integration/tasks.py
search_target = """                    if not webhook_url:
                        raise Exception(
                            "A URL do Webhook na StoreIntegration está vazia."
                        )
                    response = requests.post(
                        webhook_url, json=outbound_payload, headers=headers, timeout=5
                    )"""

replace_target = """                    if not webhook_url:
                        raise Exception(
                            "A URL do Webhook na StoreIntegration está vazia."
                        )
                    
                    # Proteção contra SSRF (Server-Side Request Forgery)
                    from urllib.parse import urlparse
                    import socket
                    import ipaddress
                    
                    parsed = urlparse(webhook_url)
                    if parsed.scheme not in ('http', 'https'):
                        raise Exception(f"Esquema de URL inválido: {parsed.scheme}")
                        
                    try:
                        ip = socket.gethostbyname(parsed.hostname)
                        ip_obj = ipaddress.ip_address(ip)
                        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                            raise Exception("Bloqueio SSRF: A URL aponta para um IP interno/privado.")
                    except Exception as e:
                        if "Bloqueio SSRF" in str(e):
                            raise e
                        raise Exception(f"Falha de resolução DNS para o Webhook: {e}")

                    # allow_redirects=False previne bypass via redirecionamento HTTP (SSRF)
                    response = requests.post(
                        webhook_url, json=outbound_payload, headers=headers, timeout=5, allow_redirects=False
                    )
                    
                    if response.status_code in [301, 302, 307, 308]:
                        raise Exception("Bloqueio SSRF: Redirecionamentos HTTP não são permitidos em Webhooks.")"""

if search_target in content:
    content = content.replace(search_target, replace_target)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SSRF vulnerability fixed successfully.")
else:
    print("Could not find the target code to replace.")

