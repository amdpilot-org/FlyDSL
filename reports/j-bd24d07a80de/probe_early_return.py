#!/usr/bin/env python3

import argparse

import torch

import flydsl.compiler as flyc
import flydsl.expr as fx
from flydsl.expr import const_expr


def build(form):
    if form == "baseline_no_return":

        @flyc.kernel
        def kernel(Out: fx.Tensor):
            Out[0] = fx.Int32(1)

        @flyc.jit
        def launcher(
            Out: fx.Tensor,
            flag: fx.Int32,
            flag_const: fx.Constexpr[int],
            stream: fx.Stream = fx.Stream(None),
        ):
            kernel(Out).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)

    elif form == "top_level_return":

        @flyc.kernel
        def kernel(Out: fx.Tensor):
            Out[0] = fx.Int32(1)
            return
            Out[0] = fx.Int32(2)

        @flyc.jit
        def launcher(
            Out: fx.Tensor,
            flag: fx.Int32,
            flag_const: fx.Constexpr[int],
            stream: fx.Stream = fx.Stream(None),
        ):
            kernel(Out).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)

    elif form == "top_level_value_return":

        @flyc.kernel
        def kernel(Out: fx.Tensor):
            return fx.Int32(1)
            Out[0] = fx.Int32(2)

        @flyc.jit
        def launcher(
            Out: fx.Tensor,
            flag: fx.Int32,
            flag_const: fx.Constexpr[int],
            stream: fx.Stream = fx.Stream(None),
        ):
            kernel(Out).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)

    elif form == "dynamic_if_return_last":

        @flyc.kernel
        def kernel(Out: fx.Tensor, flag: fx.Int32):
            if flag > fx.Int32(0):
                Out[0] = fx.Int32(1)
                return
            else:
                Out[0] = fx.Int32(2)

        @flyc.jit
        def launcher(
            Out: fx.Tensor,
            flag: fx.Int32,
            flag_const: fx.Constexpr[int],
            stream: fx.Stream = fx.Stream(None),
        ):
            kernel(Out, flag).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)

    elif form == "dynamic_if_return_after":

        @flyc.kernel
        def kernel(Out: fx.Tensor, flag: fx.Int32):
            if flag > fx.Int32(0):
                Out[0] = fx.Int32(1)
                return
            else:
                Out[0] = fx.Int32(2)
            Out[0] = fx.Int32(3)

        @flyc.jit
        def launcher(
            Out: fx.Tensor,
            flag: fx.Int32,
            flag_const: fx.Constexpr[int],
            stream: fx.Stream = fx.Stream(None),
        ):
            kernel(Out, flag).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)

    elif form == "dynamic_if_state_return":

        @flyc.kernel
        def kernel(Out: fx.Tensor, flag: fx.Int32):
            value = fx.Int32(0)
            if flag > fx.Int32(0):
                value = fx.Int32(1)
                return
            Out[0] = value

        @flyc.jit
        def launcher(
            Out: fx.Tensor,
            flag: fx.Int32,
            flag_const: fx.Constexpr[int],
            stream: fx.Stream = fx.Stream(None),
        ):
            kernel(Out, flag).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)

    elif form == "for_return_after":

        @flyc.kernel
        def kernel(Out: fx.Tensor):
            for i in range(fx.Int32(2)):
                Out[0] = fx.Int32(10) + i
                return
            Out[0] = fx.Int32(99)

        @flyc.jit
        def launcher(
            Out: fx.Tensor,
            flag: fx.Int32,
            flag_const: fx.Constexpr[int],
            stream: fx.Stream = fx.Stream(None),
        ):
            kernel(Out).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)

    elif form == "while_return_after":

        @flyc.kernel
        def kernel(Out: fx.Tensor):
            offset = fx.Int32(2)
            while offset > fx.Int32(0):
                Out[0] = offset
                return
            Out[0] = fx.Int32(99)

        @flyc.jit
        def launcher(
            Out: fx.Tensor,
            flag: fx.Int32,
            flag_const: fx.Constexpr[int],
            stream: fx.Stream = fx.Stream(None),
        ):
            kernel(Out).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)

    elif form == "nested_if_return_after":

        @flyc.kernel
        def kernel(Out: fx.Tensor, flag: fx.Int32):
            if flag > fx.Int32(0):
                if flag > fx.Int32(0):
                    Out[0] = fx.Int32(1)
                    return
                else:
                    Out[0] = fx.Int32(2)
            else:
                Out[0] = fx.Int32(3)
            Out[0] = fx.Int32(4)

        @flyc.jit
        def launcher(
            Out: fx.Tensor,
            flag: fx.Int32,
            flag_const: fx.Constexpr[int],
            stream: fx.Stream = fx.Stream(None),
        ):
            kernel(Out, flag).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)

    elif form == "constexpr_if_return_after":

        @flyc.kernel
        def kernel(Out: fx.Tensor, flag_const: fx.Constexpr[int]):
            if const_expr(flag_const > 0):
                Out[0] = fx.Int32(1)
                return
            Out[0] = fx.Int32(2)

        @flyc.jit
        def launcher(
            Out: fx.Tensor,
            flag: fx.Int32,
            flag_const: fx.Constexpr[int],
            stream: fx.Stream = fx.Stream(None),
        ):
            kernel(Out, flag_const).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)

    elif form == "constexpr_for_return_after":

        @flyc.kernel
        def kernel(Out: fx.Tensor):
            for i in fx.range_constexpr(2):
                Out[0] = fx.Int32(10) + i
                return
            Out[0] = fx.Int32(99)

        @flyc.jit
        def launcher(
            Out: fx.Tensor,
            flag: fx.Int32,
            flag_const: fx.Constexpr[int],
            stream: fx.Stream = fx.Stream(None),
        ):
            kernel(Out).launch(grid=(1, 1, 1), block=(1, 1, 1), stream=stream)

    else:
        raise ValueError(f"unknown form: {form}")

    return launcher


def main():
    forms = (
        "baseline_no_return",
        "top_level_return",
        "top_level_value_return",
        "dynamic_if_return_last",
        "dynamic_if_return_after",
        "dynamic_if_state_return",
        "for_return_after",
        "while_return_after",
        "nested_if_return_after",
        "constexpr_if_return_after",
        "constexpr_for_return_after",
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("form", choices=forms)
    parser.add_argument("--flag", type=int, default=1)
    parser.add_argument("--flag-const", type=int, default=1)
    parser.add_argument("--expected", type=int, required=True)
    args = parser.parse_args()

    launcher = build(args.form)
    out = torch.full((1,), 99, device="cuda", dtype=torch.int32)
    tensor = flyc.from_torch_tensor(out).mark_layout_dynamic(leading_dim=0, divisibility=1)
    launcher(tensor, fx.Int32(args.flag), args.flag_const)
    torch.cuda.synchronize()
    actual = out.item()
    print(
        f"RESULT form={args.form} flag={args.flag} flag_const={args.flag_const} "
        f"actual={actual} expected={args.expected}"
    )
    if actual != args.expected:
        raise AssertionError(f"numerical gate failed: actual={actual}, expected={args.expected}")


if __name__ == "__main__":
    main()
