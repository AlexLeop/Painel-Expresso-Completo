import os
with open("config/panel_api.py", "a", encoding="utf-8") as f:
    f.write("\n\n# Catch-all\n@panel_api.api_operation(['GET', 'POST', 'PUT', 'DELETE'], '/{path:path}')\ndef catch_all(request, path: str):\n    return {}\n")
print("Done appending catch-all")
