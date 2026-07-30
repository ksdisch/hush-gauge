"""Shared fixtures. The tokenizer is session-scoped: all three subjects share one, so it
loads once for the whole suite (`M0-BRIEF.md` §"A fact worth stating once")."""

from __future__ import annotations

import pytest

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


@pytest.fixture(scope="session")
def tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(MODEL)
