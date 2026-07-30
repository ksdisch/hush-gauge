"""The inherited concept roster — copied from `mute-map`, not imported (`K2`, and the
standing cut-from-your-predecessor rule).

Source: `~/Projects/mute-map/items/m1-battery.json` (`roster`, `forbidden_forms`) and
`~/Projects/mute-map/m3_matrix.py:88` (`SUBSET`, the 12 M3-characterized primes).

`ROSTER`'s key order is load-bearing: `D4` draws its first ten `shuffle` calls in
exactly this order, so reordering these keys changes the frozen battery.
"""

from __future__ import annotations

#: 10 categories × 6 concepts = 60 words. Order frozen — see module docstring.
ROSTER: dict[str, tuple[str, ...]] = {
    "countries": ("France", "Canada", "China", "Egypt", "Japan", "Brazil"),
    "months": ("February", "April", "July", "October", "January", "September"),
    "animals": ("lion", "eagle", "shark", "spider", "tiger", "bear"),
    "planets": ("Mars", "Saturn", "Venus", "Jupiter", "Mercury", "Neptune"),
    "musical instruments": ("piano", "guitar", "violin", "drum", "trumpet", "flute"),
    "precious metals": ("gold", "silver", "platinum", "copper", "bronze", "iron"),
    "gemstones": ("diamond", "ruby", "pearl", "jade", "opal", "amber"),
    "farm animals": ("cow", "pig", "horse", "sheep", "chicken", "duck"),
    "insects": ("bee", "ant", "beetle", "butterfly", "moth", "mosquito"),
    "days of the week": ("Monday", "Tuesday", "Thursday", "Friday", "Saturday", "Sunday"),
}

#: All 60 roster words, in category order.
WORDS: tuple[str, ...] = tuple(word for words in ROSTER.values() for word in words)

#: `D1` rule 2's root-changing derivatives, which a prefix match cannot catch. Covers
#: only 7 of the 60 words — the all-roster prefix rule does the rest of the work.
FORBIDDEN_FORMS: dict[str, tuple[str, ...]] = {
    "France": ("french",),
    "Canada": ("canadian",),
    "China": ("chinese",),
    "Mars": ("martian",),
    "Mercury": ("mercurial", "mercuric"),
    "Jupiter": ("jovian",),
    "iron": ("ferrous", "ferric"),
}

#: mute-map's 12 M3-characterized primes. All six `countries` words are primes, which
#: is why `K2`'s "12 guaranteed inside the battery" was unsatisfiable and the real
#: guarantee is 11 of 12 (`D9a`).
M3_PRIMES: frozenset[str] = frozenset(
    {
        "Brazil", "Canada", "China", "Egypt", "France", "Japan",
        "Jupiter", "Mars", "piano", "violin", "October", "silver",
    }
)

CATEGORIES: tuple[str, ...] = tuple(ROSTER)

assert len(WORDS) == 60 and len(set(WORDS)) == 60
assert all(len(words) == 6 for words in ROSTER.values())
assert M3_PRIMES <= set(WORDS)
