import sys, json

if len(sys.argv) < 4:
    print('Usage: compare_latency.py BASELINE DESKTOP_RESULT BROWSER_RESULT')
    sys.exit(1)

baseline = json.load(open(sys.argv[1]))
res_desktop = json.load(open(sys.argv[2]))
res_browser = json.load(open(sys.argv[3]))

fail = False
if res_desktop['latency'] is None:
    print('Desktop latency measurement failed')
    fail = True
elif res_desktop['latency'] > baseline['desktop'] * 1.15:
    print(f'Desktop latency regression: {res_desktop["latency"]} vs baseline {baseline["desktop"]}')
    fail = True

if res_browser['latency'] is None:
    print('Browser latency measurement failed')
    fail = True
elif res_browser['latency'] > baseline['browser'] * 1.15:
    print(f'Browser latency regression: {res_browser["latency"]} vs baseline {baseline["browser"]}')
    fail = True

if fail:
    sys.exit(1)
else:
    print('LLM latency within threshold')
