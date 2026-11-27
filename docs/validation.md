# Validation record

What has actually been executed, where, and how to repeat it. Newest first.

## v0.2.1 (2026-11-27): the executed DAB simulation on a clean Linux machine

Question: can the ngspice simulation that the AIPE-Workflows 10 kW dual-active-bridge example relies on be
repeated by anyone, without the Windows machine it was first recorded on?

Setup: a fresh Ubuntu 24.04 container, Python 3.13, `apt-get install ngspice` (ngspice 42),
`pip install -e ".[dev,plot]"`. Nothing else.

| Check | Result |
| --- | --- |
| `aipe-sim doctor` | ngspice 42 found on `PATH`; RC step-response qualification passed (relative errors 2e-6 and 7e-7) |
| `python -m pytest -q tests/` | 242 passed, 1 skipped, about 15 s. All solver-marked tests executed. The skip is an optional cross-check against a file of another repository (AIPE-Design-Agent) |
| Level 1 (ideal) run, Workflows specification `phi_22p5`, 12 cycles | valid steady state in 0.1 s |
| Level 2 (behavioural) run, Workflows specification `circuit-sim-level2`, 160 cycles, 1.4e5 time points | valid steady state in 7 s |

Comparison with the results recorded in AIPE-Workflows (`examples/dab-10kw/results/`, commit 6284f18,
ngspice 47 on Windows 11, 2026-10-21). The generated netlists are byte-identical (same SHA-256), so the
only differences are solver version and platform:

| Quantity (Level 2) | Linux, ngspice 42 | Windows, ngspice 47 | Relative difference |
| --- | --- | --- | --- |
| Input power | 9694.38 W | 9694.20 W | 1.9e-5 |
| Output power | 9607.95 W | 9607.83 W | 1.2e-5 |
| i_L RMS | 13.2998 A | 13.2997 A | 8e-6 |
| i_L peak | 14.3449 A | 14.3438 A | 7e-5 |
| Port 2 voltage | 392.080 V | 392.077 V | 6e-6 |
| Total loss | 131.23 W | 131.66 W | 3.3e-3 |
| Peak drain-source voltage, primary / secondary | 810.5 / 412.3 V | 810.1 / 412.3 V | 5e-4 |

Level 1 agrees to 2e-5 in power and RMS current; its total loss (5.56 W against 5.46 W) differs by 2 %
because it is a 5 W difference of two 10 kW averages. The HDF5 file hashes differ between the two machines,
as they must: the solvers choose different time points (140 121 against 139 224).

What this does and does not establish:

- The executed simulation is reproducible from this repository with the stock Ubuntu ngspice package. It
  does not depend on ngspice 47 or on Windows.
- CI now repeats the Level 2 run on every push (`tests/test_dab_level2_ngspice.py`) and fails if power,
  current or port voltage move by more than 0.1 %, or the loss by more than 3 %, from the recorded result.
  Before this release CI executed ngspice but only the Level 1 model.
- It is agreement between two versions of one solver on one model. It is not a validation of the model
  against another simulator, a manufacturer device model or a measurement; none of those exists yet.

## v0.1 record (2026-10-07), kept as written

Reviewed 2026-10-07. The 13 skill folders validate, including all eight retained
workflows and five additions. New skill metadata and instructions were checked
with the skill-creator validator. README generation is deterministic and contains
no wall-clock date. JSON/YAML/Markdown/code use LF checkout rules.

Local Python 3.10.11, python-control 0.10.2, NumPy 2.2.6 and SciPy 1.15.3:

```sh
python scripts/update_readme.py
python scripts/validate_skills.py
python pe-python-control-analysis/scripts/buck_control.py --output buck-result.json
python -m unittest discover -s tests -v
```

Five local tests passed; one ngspice test skipped because the solver was absent.
Numerical checks cover DC gain and final value across 3 input voltages and 3
loads, stable linear poles, rejection of nonphysical/nonfinite inputs, metadata
consistency, retained LTspice classification and deterministic generation.

Ubuntu CI installs ngspice and runs the switched buck at 100 ns and 50 ns maximum
time steps, checking mean output and sensitivity over the same late window.
The workflow is configured here; its actual run status is recorded by GitHub
checks on the PR. A local skip is not a completed solver run.

The manifest is validated against the coordinator's AIPE-Registry v0.1 schema
during cross-repository validation. Compatibility is mapped: no complete state
adapter, installed CAD/FEA run, MCP execution, commercial-tool run, measurement
or physical device validation is claimed. Scaffolds provide engineering input,
execution and verification requirements without fabricated output artifacts.
