"""List the OpenAI models our key can call (GET /v1/models, not billed). The token is read from a file and never
printed. usage: python list_models.py [token file (default /data/.openai_token)]"""
import json
import re
import sys
import urllib.request

path = sys.argv[1] if len(sys.argv) > 1 else "/data/.openai_token"
tok = re.search(r"sk-[A-Za-z0-9_\-]+", open(path).read()).group(0)
req = urllib.request.Request("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {tok}"})
data = json.load(urllib.request.urlopen(req, timeout=60))["data"]
ids = sorted(d["id"] for d in data)
print(len(ids), "models")
for i in ids:
    if re.match(r"^(gpt|o\d|chatgpt|computer)", i):
        print(i)
