"""Build `batteries/probe_panel.json` from `D17` + `D15`, then load it back through the
asserting loader.

Run once; the artifact is committed and never regenerated in place. A diff after a rerun
means the tokenizer, the pins, or `batteries/secrets.json` moved — a stop condition, not
a file to accept. Mirrors `build_batteries.py`, including the three-subject tokenizer
certification: the panel's probe rows are token ids, so "the three scales share one
tokenizer" has to be asserted here too and not inherited as a memory.

    uv run python build_probe_panel.py
"""

from __future__ import annotations

import json

from transformers import AutoTokenizer

import battery
import panel
from build_batteries import SUBJECTS


def main() -> None:
    tokenizers = [AutoTokenizer.from_pretrained(name) for name in SUBJECTS]
    battery.certify_tokenizers(tokenizers)
    print(f"tokenizer certification: {len(SUBJECTS)} subjects agree on all 60 roster words")

    payload = panel.build(tokenizers[0])
    panel.PANEL_PATH.write_text(json.dumps(payload, indent=1) + "\n")

    loaded = panel.load()
    rows = loaded["words"]
    print(f"\nprobe_panel.json  sha256 {battery.sha256(panel.PANEL_PATH)}")
    print(f"cross step {loaded['cross_step']} on index_in_category (D17)")

    forms = {name: sum(1 for r in rows if r["form_used"] == name) for name in ("bare", "leading_space")}
    caps = {name: sum(1 for r in rows if r["cap_form_used"] == name) for name in panel.CAP_FORMS}
    print(f"probe rows (D15):     {forms}")
    print(f"cap companion rows:   {caps}")
    print(f"  absent:  {sorted(r['word'] for r in rows if r['cap_form_used'] == 'absent')}")
    lowercase = [r for r in rows if r["word"][:1].islower() and r["cap_form_used"] != "absent"]
    fallback = [r for r in lowercase if r["cap_form_used"] != r["form_used"]]
    print(f"  case-matched {len(lowercase) - len(fallback)} / fallback {len(fallback)}: "
          f"{sorted(r['word'] for r in fallback)}")

    crossing = loaded["split_crossing"]
    print(f"\nsplit crossing (D17, computed): calibration→eval "
          f"{crossing['calibration_to_eval']}/25, eval→calibration "
          f"{crossing['eval_to_calibration']}/25")


if __name__ == "__main__":
    main()
