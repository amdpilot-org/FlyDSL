# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 FlyDSL Project Contributors

"""Regression tests for concrete compiler and utility docstring examples."""

import inspect
import textwrap

from flydsl.compiler.backends.base import BaseBackend, GPUTarget
from flydsl.utils.env import EnvManager, EnvOption


def test_reviewed_public_doc_examples_execute():
    """The four independently reported counterexamples are runnable."""

    for symbol in (GPUTarget, BaseBackend, EnvOption, EnvManager):
        doc = inspect.getdoc(symbol)
        assert doc and "Example:" in doc
        example = textwrap.dedent(doc.split("Example:\n", 1)[1])
        assert len(example.splitlines()) <= 5
        exec(example, {})
