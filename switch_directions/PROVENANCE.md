# switch_directions/PROVENANCE.md

`D38`'s constructed Arm B candidates. The `.pt` files are gitignored (they are a
function of the frozen capture, the frozen seeds and the recorded rule, and are
rebuildable by `construct_switch.py`); **this table is the tracked fingerprint**,
and `gates/g4.py` refuses a payload whose recorded direction SHA256s do not match
it (`D39`.5 arm 7). The `real`/`sham` SHA256s are of the float32 `[n_band_layers,
d_model]` matrices themselves, not of the container file, so a re-save cannot
change them and a changed direction cannot hide behind one.

| artifact | file sha256 | real w sha256 | deciding sham sha256 |
|---|---|---|---|
| `qwen2.5-0.5b-instruct.pt` | `67e43856a5cc428cf7506ae6e744a576a6b48d07bcfdc1faca7f6fd901176a6f` | `a089b9ffcaca11b85643497b6976f8e3a1cd3c378bcf9ba52e0b842539509904` | `30365897adaf44f22b15b6cec428ca9d679ed6cfb1f7842a6df3f1bbaa784be4` |
| `qwen2.5-1.5b-instruct.pt` | `1b8e15e91095189a61199777ba7c591bd6853909b76b61559bcd91de135f6df5` | `f8ed7704fb943e12c5f56a0213310505cf79e2fa4327d51666d2f6b920f526b0` | `38bf5eaf01e30b6cb28ab720d307d16b47f9e2c528c0a21c265326140de9f771` |
| `qwen2.5-3b-instruct.pt` | `29e34ab4556a26a507dee880e292994c8f9ec041c88f5ae2e3a5a01ee2d55f18` | `d49c849bcd97a7d1c1c94a8d9007a1d9b1e92060ee4ffff8aff5174aa1ab0651` | `175b550671fceb3bc96a1bb74a2b088690e5d69cea3edc2c37c8cbabedccbc56` |
