"""Tests for cyclomatic complexity analyzer."""

from aura_cli.core.quality.complexity_analyzer import analyze_complexity


def test_simple_function_low_complexity():
    source = """
def hello(name):
    return f"Hello, {name}"
"""
    results = analyze_complexity(source)
    assert len(results) == 1
    assert results[0]["function"] == "hello"
    assert results[0]["complexity"] == 1
    assert results[0]["severity"] == "low"


def test_medium_complexity():
    source = """
def process(x, y):
    if x > 0:
        for i in range(y):
            if i % 2 == 0:
                print(i)
            elif i % 3 == 0:
                print("fizz")
    return x
"""
    results = analyze_complexity(source)
    assert len(results) == 1
    assert results[0]["function"] == "process"
    assert results[0]["severity"] == "medium"
    assert results[0]["complexity"] >= 5


def test_high_complexity():
    source = """
def complex_func(a, b, c):
    if a:
        if b:
            if c:
                pass
    for i in range(10):
        if i > 5:
            pass
        elif i > 3:
            pass
    while a and b:
        try:
            pass
        except ValueError:
            pass
        except TypeError:
            pass
    assert a or b
    return [x for x in range(10) if x > 5]
"""
    results = analyze_complexity(source)
    assert len(results) == 1
    assert results[0]["function"] == "complex_func"
    assert results[0]["severity"] == "high"
    assert results[0]["complexity"] > 10


def test_class_methods():
    source = """
class MyClass:
    def simple(self):
        return 1

    def branchy(self, x):
        if x > 0:
            if x > 10:
                return "big"
            return "small"
        return "negative"
"""
    results = analyze_complexity(source)
    assert len(results) == 2
    assert results[0]["function"] == "MyClass.simple"
    assert results[1]["function"] == "MyClass.branchy"
    assert results[1]["complexity"] >= 3


def test_syntax_error_returns_empty():
    results = analyze_complexity("def broken(:\n")
    assert results == []


def test_boolean_operators_count():
    source = """
def check(a, b, c, d):
    if a and b and c or d:
        return True
    return False
"""
    results = analyze_complexity(source)
    assert results[0]["complexity"] >= 4  # 1 base + 1 if + 2 and + 1 or
