import ast

from flydsl.compiler.ast_rewriter import (
    CanonicalizeWhile,
    InsertEmptyYieldForSCFFor,
    ReplaceIfWithDispatch,
    ReplaceYieldWithSCFYield,
    RewriteBoolOps,
)


def _node_types(source):
    return {type(node) for node in ast.walk(ast.parse(source))}


def test_straight_line_ast_skips_control_flow_rewriters():
    node_types = _node_types("def f(x):\n    y = x + 1\n    return y\n")

    assert not RewriteBoolOps.is_applicable(node_types)
    assert not ReplaceIfWithDispatch.is_applicable(node_types)
    assert not InsertEmptyYieldForSCFFor.is_applicable(node_types)
    assert not ReplaceYieldWithSCFYield.is_applicable(node_types)
    assert not CanonicalizeWhile.is_applicable(node_types)


def test_generated_node_dependencies_keep_downstream_rewriters_enabled():
    bool_types = _node_types("def f(a, b):\n    return a and b\n")
    for_types = _node_types("def f(n):\n    for i in range(n):\n        pass\n")

    assert RewriteBoolOps.is_applicable(bool_types)
    assert ReplaceIfWithDispatch.is_applicable(bool_types)  # BoolOp becomes IfExp.
    assert InsertEmptyYieldForSCFFor.is_applicable(for_types)
    assert ReplaceYieldWithSCFYield.is_applicable(for_types)  # For may gain Yield.


def test_each_supported_control_flow_construct_selects_its_rewriter():
    cases = [
        ("def f(x):\n    if x:\n        return 1\n    return 0\n", ReplaceIfWithDispatch),
        ("def f(x):\n    return 1 if x else 0\n", ReplaceIfWithDispatch),
        ("def f(n):\n    while n:\n        n -= 1\n", CanonicalizeWhile),
        ("def f():\n    yield 1\n", ReplaceYieldWithSCFYield),
    ]

    for source, rewriter in cases:
        assert rewriter.is_applicable(_node_types(source))
