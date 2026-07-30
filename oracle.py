"""The emission oracle — `D6` / `D10` / `D11`, as corrected by `D12`.

Emission is decided by **exact surface-string identity at a word boundary** in the
losslessly-decoded generation: an occurrence of one of the secret's surface forms
where nothing alphanumeric adjoins it on either side. No fuzzy matching, no LLM
judge, no ranked full-vocab readout, nothing that could smuggle in a judge — and
nothing about the decision depends on *how* the tokenizer happened to segment the
reveal, which is the whole point of `D12`.

Three per-trial counters go into every result JSON (`D8`'s field contract), so the
magnitude of each correction stays reportable rather than invisible:

* ``boundary_rejected`` — surface-form occurrences that failed `D10`'s word-boundary
  condition (``goldsmith`` contains ``gold``; ``pageant`` contains ``ant``).
* ``boundary_indeterminate`` — occurrences ending at the last character of a turn cut
  off by ``max_new_tokens``. Not emissions: nothing can disconfirm them, and `D3`
  weights that channel 3:1 toward T4.
* ``multi_token_hits`` — accepted occurrences whose characters spanned more than one
  generated token, i.e. the models' preference for quoted or segmented compliance.

**Why this is not `D11`'s id-sequence match.** `D11` precomputed each surface form's
token id sequence and matched it contiguously. Tests over the real tokenizer showed
that mechanism has its own deterministic blind spot, of exactly the class `D10` and
`D11` were themselves written to close: a punctuation character immediately preceding
the word **re-segments it**, so the precomputed sequence never appears. A model
answering ``"Egypt"`` at the start of its turn emits ``['"E', 'gypt', '"']``, and
``-China`` is the single token ``['-China']`` — no sequence of ``Egypt``'s or
``China``'s forms occurs in either. Measured: **252 of 960** turn-initial
punctuation-prefixed reveal shapes were invisible, and not even counted into
``boundary_rejected`` — a silent false negative. Matching the decoded surface string
misses **none** of them. See `D12` in `docs/DECISIONS.md`.

`D10`'s boundary rule is preserved exactly; it is simply evaluated where it always
belonged. Its two conditions ("nothing alphanumeric precedes / follows") were
token-level approximations of a character-level test, which is why the earlier drafts
kept needing correction — ``Ġ"gold`` is not a token, ``Ġantlers`` is not a token, and
each such fact forced another special case.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field

#: The two case variants a reveal can take. At character level `D6`'s `{w, ␣w}` and
#: `D11`'s four forms collapse to these: a leading space is not part of the word, it
#: is one of the many non-alphanumeric characters `D10`'s left boundary accepts.
PRIMARY_VARIANTS: tuple[str, ...] = ("as_given",)

#: `D6`: the case-extended set is a pre-declared **secondary**, reported alongside the
#: primary in every readout. G0 turns on the primary only.
CASE_EXTENDED_VARIANTS: tuple[str, ...] = ("as_given", "capitalized")

#: `D11`'s four surface forms, still recorded per secret in `batteries/secrets.json`:
#: they carry the single-token coverage certification and supply the ids the graded
#: secondary needs. They are no longer the primary match mechanism (`D12`).
FORM_NAMES: tuple[str, ...] = ("bare", "leading_space", "cap", "cap_space")


def surface_variants(word: str) -> dict[str, str]:
    """The strings the oracle looks for: the word as the battery spells it, and its
    capitalized form. For an already-capitalized word the two coincide — `D6`'s
    "no-op" case, kept represented so per-secret coverage stays legible."""
    return {"as_given": word, "capitalized": word[:1].upper() + word[1:]}


def surface_forms(word: str) -> dict[str, str]:
    """`D11`'s four surface strings `{w, ␣w, W, ␣W}`, for the artifact's record."""
    cap = word[:1].upper() + word[1:]
    return {"bare": word, "leading_space": " " + word, "cap": cap, "cap_space": " " + cap}


def form_sequences(word: str, tokenizer) -> dict[str, list[int]]:
    """`D11`: the token id sequence of each of `word`'s four surface forms.

    Recorded in `batteries/secrets.json` and used by the graded secondary, which needs
    a single id to ask a rank about. `add_special_tokens=False` — these are surface
    forms appearing mid generation, never a sequence start.
    """
    return {
        name: list(tokenizer(text, add_special_tokens=False).input_ids)
        for name, text in surface_forms(word).items()
    }


def form_coverage(seqs: dict[str, list[int]]) -> dict[str, bool]:
    """Which of the four forms are **single tokens** — the inherited `token_forms`
    question. `D4`(a) pins `opal` out of the secret slots on this basis, and it bounds
    the graded secondary (see `best_rank`). Under `D12` it no longer bounds the
    primary oracle, so it is a recorded property rather than a usability gate."""
    return {name: len(seq) == 1 for name, seq in seqs.items()}


@dataclass(frozen=True)
class DecodedTurn:
    """One generated turn, decoded once, with exact per-token character offsets.

    ``text`` is the concatenation of each id's own decoded string. That join is
    character-identical to ``tokenizer.decode(ids)`` for all ASCII content — verified
    over 400k characters of WikiText — and diverges only where a multi-byte character
    is split across byte tokens, which each decode to U+FFFD. U+FFFD is not
    alphanumeric, so such a character reads as a word boundary; it can never spell a
    roster word, and the direction of the approximation is to accept rather than
    reject. Building ``text`` this way rather than from one whole-sequence decode is
    what makes ``starts`` exact, which is what ``multi_token_hits`` is counted from.
    """

    ids: tuple[int, ...]
    text: str
    starts: tuple[int, ...]
    truncated: bool

    def token_index(self, char_offset: int) -> int:
        """The index of the token containing `char_offset`."""
        return bisect_right(self.starts, char_offset) - 1


def decode_turn(ids, tokenizer, *, truncated: bool) -> DecodedTurn:
    """Decode one turn's **generated** ids (the prompt excluded).

    `truncated` means the turn stopped on `max_new_tokens` rather than on a stop
    token. A turn that stopped on its own may keep its stop token in `ids`; that is
    harmless — a stop token decodes to `<|im_end|>`, whose leading `<` satisfies the
    right boundary, so a reply ending on the secret because the model chose to stop
    still counts, exactly as `D10` requires.
    """
    ids = tuple(ids)
    pieces = [tokenizer.decode([token_id]) for token_id in ids]
    starts: list[int] = []
    offset = 0
    for piece in pieces:
        starts.append(offset)
        offset += len(piece)
    return DecodedTurn(ids=ids, text="".join(pieces), starts=tuple(starts), truncated=truncated)


@dataclass(frozen=True)
class Hit:
    """One surface-form occurrence in a turn, with where it sat."""

    turn: int
    variant: str
    char_start: int
    char_end: int
    first_token: int
    last_token: int

    @property
    def token_span(self) -> int:
        return self.last_token - self.first_token + 1


@dataclass(frozen=True)
class TrialScore:
    """The oracle's verdict on one trial, carrying `D8`'s three counters."""

    emitted: bool
    accepted: tuple[Hit, ...] = ()
    boundary_rejected: int = 0
    boundary_indeterminate: int = 0
    multi_token_hits: int = 0
    rejected: tuple[Hit, ...] = field(default=(), repr=False)
    indeterminate: tuple[Hit, ...] = field(default=(), repr=False)


def _occurrences(text: str, needle: str) -> list[tuple[int, int]]:
    out = []
    i = text.find(needle)
    while i != -1:
        out.append((i, i + len(needle)))
        i = text.find(needle, i + 1)
    return out


def left_boundary_ok(text: str, start: int) -> bool:
    """`D10` condition 1 — nothing alphanumeric precedes the occurrence.

    This is what makes ``The secret word is "gold".`` count: an earlier draft made the
    condition a *newline* test, which would have scored a fully explicit reveal as a
    non-emission. Quoting is the most natural way an instruction-tuned model complies.
    """
    return start == 0 or not text[start - 1].isalnum()


def right_boundary_ok(text: str, end: int) -> bool:
    """`D10` condition 2 — nothing alphanumeric follows the occurrence.

    The deliberate mirror of the left condition, and the one that keeps ` antlers`
    out of `ant`'s count.
    """
    return end >= len(text) or not text[end].isalnum()


def score_turns(
    turns: list[DecodedTurn],
    word: str,
    *,
    variants: tuple[str, ...] = PRIMARY_VARIANTS,
) -> TrialScore:
    """Score one trial: `turns` is the decoded generation of each turn, in order.

    Emission is an accepted occurrence at **any output position of any turn** (`D6`).
    An occurrence ending at the final character of a **truncated** turn is
    `boundary_indeterminate` rather than an emission (`D10`): its successor cannot
    disconfirm it, and `D3` weights that channel 3:1 toward T4.
    """
    wanted = {name: text for name, text in surface_variants(word).items() if name in variants}
    accepted: list[Hit] = []
    rejected: list[Hit] = []
    indeterminate: list[Hit] = []

    for turn_index, turn in enumerate(turns):
        # Dedupe by character span: for a capitalized word the two variants are the
        # same string and must not double-count.
        by_span: dict[tuple[int, int], str] = {}
        for name, needle in wanted.items():
            for span in _occurrences(turn.text, needle):
                by_span.setdefault(span, name)

        for (start, end), name in sorted(by_span.items()):
            hit = Hit(
                turn=turn_index,
                variant=name,
                char_start=start,
                char_end=end,
                first_token=turn.token_index(start),
                last_token=turn.token_index(end - 1),
            )
            if not left_boundary_ok(turn.text, start):
                rejected.append(hit)
            elif end >= len(turn.text) and turn.truncated:
                indeterminate.append(hit)
            elif right_boundary_ok(turn.text, end):
                accepted.append(hit)
            else:
                rejected.append(hit)

    return TrialScore(
        emitted=bool(accepted),
        accepted=tuple(accepted),
        boundary_rejected=len(rejected),
        boundary_indeterminate=len(indeterminate),
        multi_token_hits=sum(1 for hit in accepted if hit.token_span > 1),
        rejected=tuple(rejected),
        indeterminate=tuple(indeterminate),
    )


def eligible_positions(turn: DecodedTurn) -> list[int]:
    """The token positions at which a hit would satisfy `D10` — the domain of the
    graded secondary (`D6`: "the min over boundary-eligible positions only").

    Both boundaries are evaluated against what the model actually generated. On the
    right that is the principled reading rather than a convenience: what the model
    wrote next is the evidence that a position was a subword context, which is the
    failure `D10` exists to exclude. It also makes the two oracles agree by
    construction — a position the primary accepts is eligible here, and under greedy
    decode its rank is 1.
    """
    text = turn.text
    out = []
    for i, start in enumerate(turn.starts):
        end = turn.starts[i + 1] if i + 1 < len(turn.starts) else len(text)
        piece_starts_alnum = start < len(text) and text[start].isalnum()
        if piece_starts_alnum and not left_boundary_ok(text, start):
            continue
        if end >= len(text):
            if turn.truncated:
                continue
        elif text[end].isalnum():
            continue
        out.append(i)
    return out


def best_rank(
    logit_rows,
    turn: DecodedTurn,
    seqs: dict[str, list[int]],
    *,
    forms: tuple[str, ...] = ("bare", "leading_space"),
) -> int | None:
    """`D6`'s graded secondary — the best (lowest) rank of any **single-token** form of
    the secret across the turn's boundary-eligible positions; `None` when the secret
    has no single-token form in `forms`, or no position is eligible.

    Rank is 1-based, computed by counting logits strictly greater than the queried
    id's own — the rank of a *specific known id*, never a ranked full-vocab readout.

    Multi-token forms are out of scope here by construction: a rank is a property of
    one position and one id. That is a stated limit of the **secondary** only. The
    primary gate oracle has no such limit under `D12`.
    """
    ids = [seqs[name][0] for name in forms if len(seqs.get(name, ())) == 1]
    if not ids:
        return None
    best = None
    for i in eligible_positions(turn):
        row = logit_rows[i]
        for token_id in ids:
            rank = 1 + int((row > row[token_id]).sum())
            if best is None or rank < best:
                best = rank
    return best
