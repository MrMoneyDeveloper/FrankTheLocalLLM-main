import time


def slow_add(x: int, y: int) -> int:
    """Simulate a slow addition"""
    time.sleep(0.01)
    return x + y


def test_add_bench(benchmark):
    result = benchmark(slow_add, 2, 3)
    assert result == 5
