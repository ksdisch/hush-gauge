"""`D15`'s produced-from alignment, tested against the substrate.

**This is the one assumption in M1 that, if wrong, silently invalidates every number.**
`D15` fixes the scored residual for generated token `i` as the one at *the step that
produced it* — the turn's final prompt position for `i = 0`, the decode step fed token
`i−1` otherwise. `probe.capture_producing_rows` implements that as `residual[0, -1]`, on
the reasoning that prefill's last row and a decode step's only row are the same thing.

Every other check M1 runs would pass under a one-position shift. `D16`'s byte-identity
check compares *generations*, and the hook does not touch them. `stack_captured`'s length
assertion rules out an off-by-N in the *count*, not a systematic wrong-row choice. The
`.npz`, the aggregates and both gates would all be internally consistent and uniformly
wrong. `D15` says so explicitly: "a shift between the two is invisible in the output,
which is exactly why it is pinned here rather than left to the build."

So it is tested the only way that settles it — **on a real model, through the production
context manager, against ground truth the model itself supplies.** Hook the final decoder
block, capture what the rule selects, unembed each captured row, and require its argmax to
be the token that step actually emitted.

**What writing this test found.** The first version compared the recomputed argmax against
the emitted token directly and failed on 2 of 12 steps — by 1.60 and 0.26 logits, not by
floating-point noise, with the other 10 bit-identical. The cause is not the alignment:
Qwen2.5-Instruct ships `repetition_penalty: 1.1` in its `generation_config`, and a
repetition penalty is a **logits processor**, not a sampling parameter, so it applies under
`do_sample=False` as well. The two disagreeing steps were exactly the tokens already in
context. That is a property of `D5`'s inherited generation call, discovered here and
recorded in `docs/M1-RESULTS.md`; it is uniform across every tier, arm and scale, and M1
reproduces M0 byte-for-byte under it. Nothing about it is changed — changing the decode
rule would invalidate `D16` and G0.

So the alignment is proven twice: once against clean argmax ground truth with the penalty
disabled, and once through the sweep's own settings with the penalty applied.
"""

from __future__ import annotations

import pytest
import torch

import probe

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
PROMPT = "The capital of France is"
MAX_NEW_TOKENS = 12


@pytest.fixture(scope="module")
def subject():
    transformers = pytest.importorskip("transformers")
    model = transformers.AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32)
    model.eval()
    return model, transformers.AutoTokenizer.from_pretrained(MODEL)


def _unembed(model, residual: torch.Tensor) -> torch.Tensor:
    """`dim-stage/fitter.py:115-118`'s `unembed`: final norm, then the LM head — the same
    path the model's own forward takes from the last block's output residual to logits."""
    weight = model.lm_head.weight
    return model.lm_head(model.model.norm(residual.to(weight.dtype).to(weight.device)))


def _run(model, tokenizer, prompt_ids, **kwargs):
    """One greedy generation with the final block's producing rows captured, through the
    **production** context manager."""
    final = model.config.num_hidden_layers - 1
    with probe.capture_producing_rows(
        model.model.layers, [final], lambda index, h: h.clone()
    ) as captured:
        with torch.no_grad():
            out = model.generate(
                prompt_ids, max_new_tokens=MAX_NEW_TOKENS, do_sample=False,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id, **kwargs,
            )
    return out[0, prompt_ids.shape[1] :].tolist(), captured[final], out


def test_the_captured_row_is_the_one_that_produced_the_token(subject):
    """The ground-truth test, with the repetition penalty disabled so that greedy decode
    makes each step's raw argmax *the* token it emitted — the model supplies its own
    answer key, exactly."""
    model, tokenizer = subject
    prompt_ids = tokenizer(PROMPT, return_tensors="pt").input_ids
    generated, rows, _ = _run(model, tokenizer, prompt_ids, repetition_penalty=1.0)

    assert len(rows) == len(generated), (
        "one captured residual per generated token — D15's exact len(turn.ids) per turn"
    )
    with torch.no_grad():
        predicted = [int(_unembed(model, row).argmax()) for row in rows]
    assert predicted == generated, (
        "the captured row at step i must be the row whose readout emitted generated token "
        f"i.\n  captured argmax: {tokenizer.decode(predicted)!r}\n  actually emitted: "
        f"{tokenizer.decode(generated)!r}\nA one-position shift here is invisible in the "
        "output and would make every M1 number uniformly wrong (D15)."
    )


def test_the_alignment_holds_under_the_sweeps_own_generation_settings(subject):
    """The same proof through the call the sweep actually makes — `do_sample=False` with
    the model's `generation_config` untouched, so `repetition_penalty=1.1` is live.

    Applying that penalty to the recomputed logits reproduces the emitted token at every
    step. Two things follow: the alignment is right under the real settings, and the
    penalty is genuinely in the loop, since without it the run diverges (asserted below).
    """
    transformers = pytest.importorskip("transformers")
    model, tokenizer = subject
    prompt_ids = tokenizer(PROMPT, return_tensors="pt").input_ids
    generated, rows, out = _run(model, tokenizer, prompt_ids)

    penalty = model.generation_config.repetition_penalty
    assert penalty and penalty != 1.0, (
        "Qwen2.5-Instruct ships repetition_penalty=1.1; if that ever stops being true this "
        "test is checking nothing and D5's 'greedy' would mean plain argmax after all"
    )
    processor = transformers.RepetitionPenaltyLogitsProcessor(penalty)
    predicted = []
    with torch.no_grad():
        for step, row in enumerate(rows):
            context = out[:, : prompt_ids.shape[1] + step]
            logits = _unembed(model, row).unsqueeze(0)
            predicted.append(int(processor(context, logits)[0].argmax()))
    assert predicted == generated, (
        f"emitted {tokenizer.decode(generated)!r}, recomputed "
        f"{tokenizer.decode(predicted)!r} through residual -> norm -> lm_head -> "
        "repetition penalty"
    )

    raw = [int(_unembed(model, row).argmax()) for row in rows]
    assert raw != generated, (
        "the penalty must actually change the trajectory here, or this test would pass "
        "for the wrong reason"
    )


def test_the_rejected_alternative_would_have_failed_this_test(subject):
    """The alternative `D15` rejected — the residual at the position *holding* each
    generated token — is the row produced one step **later**. Constructed from the same
    capture so the contrast is exact rather than asserted: shifting by one turns the
    answer key into the *next* token everywhere, which is precisely the silent failure.

    It also has no residual at all for a turn's final token: nothing is ever fed after it,
    so "every position of every turn" would quietly mean all-but-one.
    """
    model, tokenizer = subject
    prompt_ids = tokenizer(PROMPT, return_tensors="pt").input_ids
    generated, rows, _ = _run(model, tokenizer, prompt_ids, repetition_penalty=1.0)
    with torch.no_grad():
        predicted = [int(_unembed(model, row).argmax()) for row in rows]

    shifted = predicted[1:]                 # the "row holding token i" reading
    assert shifted != generated[: len(shifted)], "the two alignments must be distinguishable"
    assert shifted == generated[1 : len(shifted) + 1], (
        "the shifted reading predicts the NEXT token at every step — the exact off-by-one "
        "D15 rules out, and the reason the alignment is pinned in the brief"
    )
    assert len(shifted) == len(generated) - 1, "and it has no row for the turn's final token"


def test_the_band_cosine_capture_uses_the_same_alignment(subject):
    """`capture_band_cosines` is `capture_producing_rows` with the `D15` projection as its
    transform, so the alignment proven above is the alignment the sweep ran under — not a
    second implementation that happens to look similar."""
    model, tokenizer = subject
    prompt_ids = tokenizer(PROMPT, return_tensors="pt").input_ids
    final = model.config.num_hidden_layers - 1
    direction = torch.nn.functional.normalize(torch.randn(1, model.config.hidden_size), dim=1)

    _, rows, _ = _run(model, tokenizer, prompt_ids)
    with probe.capture_band_cosines(model.model.layers, {final: direction}) as cos_capture:
        with torch.no_grad():
            model.generate(prompt_ids, max_new_tokens=MAX_NEW_TOKENS, do_sample=False,
                           pad_token_id=tokenizer.eos_token_id)

    assert len(rows) == len(cos_capture[final])
    for row, cos in zip(rows, cos_capture[final], strict=True):
        assert torch.allclose(cos, direction @ (row / row.norm()), atol=1e-5)
