from pathlib import Path
p = Path("zoho/services.py")
lines = p.read_text().splitlines()
index = 237
lines[index] = "        headers = {'Authorization': f\"Zoho-oauthtoken {access_token}\"}"
p.write_text('\n'.join(lines) + '\n')
print('patched')
