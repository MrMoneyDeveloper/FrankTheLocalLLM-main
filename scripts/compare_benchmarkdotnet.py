import sys, csv

if len(sys.argv) < 3:
    print("Usage: compare_benchmarkdotnet.py BASELINE CURRENT")
    sys.exit(1)

baseline_file, current_file = sys.argv[1], sys.argv[2]

def get_mean(path):
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Method'] == 'ExecuteScalar':
                try:
                    return float(row['Mean'])
                except ValueError:
                    return None
    return None

baseline = get_mean(baseline_file)
current = get_mean(current_file)

if baseline is None or current is None:
    print("Benchmark data missing")
    sys.exit(1)

if current > baseline * 1.10:
    print(f"Performance regression: {current} vs baseline {baseline}")
    sys.exit(1)
else:
    print("Benchmark within threshold")
