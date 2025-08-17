import sys
import time
import json
import requests

base_url = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8001'
start = time.time()
try:
    requests.post(f'{base_url}/api/chat', json={'message': 'hi'}).raise_for_status()
    latency = time.time() - start
except Exception:
    latency = None
print(json.dumps({'latency': latency}))
