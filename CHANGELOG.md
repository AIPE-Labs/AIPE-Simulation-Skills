# Changelog

## 0.2.1 — 2026-11-27

First tagged release, published from the AIPE-Labs organisation. Version 0.2.0 was never tagged; results
recorded with it (for example in AIPE-Workflows) carry `0.2.0` in their provenance. For the same
specification 0.2.1 generates a byte-identical netlist and the Python API is unchanged.

- Licence: MIT (`LICENSE`, `pyproject.toml`, `aipe.yaml`). The repository previously declared no licence.
- Metadata and links point to `AIPE-Labs`; the Engineering State schema reference uses the AIPE-Core
  v0.1.0 identifier under `https://raw.githubusercontent.com/AIPE-Labs/AIPE-Core/v0.1.0/schemas/`.
- Reproducibility: the Level 2 (behavioural) DAB run that AIPE-Workflows relies on is now executed in CI
  with the Ubuntu ngspice package and compared with the result recorded on Windows with ngspice 47
  (`tests/test_dab_level2_ngspice.py`, `docs/validation.md`).
- The layout of `waveforms.h5` is documented (`docs/waveform-dataset.md`) and pinned by a test. The format
  itself (`aipe-waveform-dataset/0.1`) is unchanged.
- CLI: `aipe-sim dab run --analytic-start` starts from the analytic periodic series current, so the
  default 10 kW example is a valid steady state in 24 cycles. Without it the default circuit needs about
  130 cycles, and the README command used to report `not_steady_state`.
- CLI, behaviour change: `aipe-sim dab run` now exits with 2 when the solver completes but the result is
  not a valid periodic steady state (previously 0). 0 still means valid, 1 still means the solver failed.
  `run_dab` and the rest of the Python API are unaffected.
- Python 3.13 added to the CI matrix.
- Documentation corrected where it claimed more or less than the evidence: Level 2 total loss (132 W, not
  136 W), reproduction commands, the validation record, and a plain statement that the proprietary-tool
  skills are written procedures that bundle and execute nothing. `docs/review-2026-11.md` lists the open
  problems that were not fixed in this release.

## 0.2.0 — 2026-10-21 (not tagged)

- `aipe_simulation` package: ngspice location, qualification and batch runner, raw-file parser, DAB
  circuit specification and netlist generator (Level 1 ideal, Level 2 behavioural), waveform dataset and
  analysis engine, host-side single-phase-shift control baseline, `aipe-sim` CLI.

## 0.1.0 — 2026-10-07 (not tagged)

- Thirteen agent skills with `skills.json`, tool policy and capability manifest.
