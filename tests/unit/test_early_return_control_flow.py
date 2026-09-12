# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

import pytest

from flydsl.compiler.ast_rewriter import ASTRewriter


def test_rejects_return_in_dynamic_if():
    def sample(flag):
        if flag:
            return 1
        return 2

    with pytest.raises(SyntaxError, match=r"dynamic if \(scf\.if\)") as exc_info:
        ASTRewriter.transform(sample)
    assert exc_info.value.filename == __file__
    assert exc_info.value.lineno == sample.__code__.co_firstlineno + 2


def test_rejects_return_nested_under_dynamic_control_flow():
    def sample(n, flag):
        while n:
            if flag:
                for _ in range_constexpr(2):
                    return 1
            n -= 1
        return 2

    with pytest.raises(SyntaxError, match=r"dynamic while \(scf\.while\)") as exc_info:
        ASTRewriter.transform(sample)
    assert exc_info.value.filename == __file__
    assert exc_info.value.lineno == sample.__code__.co_firstlineno + 4


def test_rejects_return_in_dynamic_for():
    # Define this normally (rather than through exec) so inspect.getsource(), which
    # is part of the real AST rewriting path, sees stable source locations.
    def sample(n):
        for i in range(n):
            if i:
                return i
        return n

    with pytest.raises(SyntaxError, match=r"dynamic for loop \(scf\.for\)"):
        ASTRewriter.transform(sample)


def test_allows_function_level_and_compile_time_conditional_return():
    def sample(flag):
        if const_expr(flag):
            return 7
        return 9

    rewritten = ASTRewriter.transform(sample)
    assert rewritten(True) == 7
    assert rewritten(False) == 9


def test_allows_returns_in_compile_time_loops():
    def for_sample():
        for _ in range_constexpr(2):
            return 5
        return 9

    def while_sample(flag):
        while const_expr(flag):
            return 6
        return 8

    rewritten_for = ASTRewriter.transform(for_sample)
    rewritten_while = ASTRewriter.transform(while_sample)
    assert rewritten_for() == 5
    assert rewritten_while(True) == 6
    assert rewritten_while(False) == 8


def test_nested_function_return_is_its_own_function_control_flow():
    def sample(flag):
        if flag:
            def helper():
                return 4

            value = helper()
        else:
            value = 5
        return value

    # A return in a nested Python function is not an early return from the
    # surrounding DSL region and must not be rejected by the audit.
    ASTRewriter.transform(sample)
