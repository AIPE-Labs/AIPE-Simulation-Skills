#!/usr/bin/env python3
"""Generate README.md from skill metadata and package metadata.

The README follows the AIPE README template (Features / Installation / Usage /
Project Information / Documentation) with one generated section, the skill
catalogue, built from ``*/SKILL.md`` and ``skills.json``. The package version
is read from ``pyproject.toml`` so the README cannot drift from the release.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
PYPROJECT = ROOT / "pyproject.toml"

PLANNED_SKILLS: list[dict[str, str]] = []


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise ValueError(f"Missing frontmatter: {path}")

    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def first_heading(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.parent.name


def package_version() -> str:
    """Return the ``[project]`` version from pyproject.toml (tomllib needs Python 3.11)."""
    match = re.search(r'^version\s*=\s*"([^"]+)"', PYPROJECT.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise ValueError("pyproject.toml declares no [project] version")
    return match.group(1)


def skill_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    policy = {s['id']: s for s in json.loads((ROOT / 'skills.json').read_text(encoding="utf-8"))['skills']}
    for skill_md in sorted(ROOT.glob("*/SKILL.md")):
        if skill_md.parts[-2].startswith("."):
            continue
        meta = parse_frontmatter(skill_md)
        references = sorted((skill_md.parent / "references").glob("*.md"))
        agents = skill_md.parent / "agents" / "openai.yaml"
        rows.append(
            {
                "folder": skill_md.parent.name,
                "name": meta.get("name", skill_md.parent.name),
                "title": first_heading(skill_md),
                "description": meta.get("description", ""),
                "references": str(len(references)),
                "status": policy[skill_md.parent.name]['maturity'] if agents.exists() else "draft",
                "access": policy[skill_md.parent.name]['access'],
            }
        )
    return rows


def generate() -> str:
    rows = skill_rows()
    version = package_version()

    active_table = "\n".join(
        [
            "| Skill | Maturity | Access | Focus | References |",
            "| --- | --- | --- | --- | ---: |",
            *[
                f"| [`{row['name']}`](./{row['folder']}/SKILL.md) | {row['status']} | {row['access']} | {row['title']} | {row['references']} |"
                for row in rows
            ],
        ]
    )

    planned_section = ""
    if PLANNED_SKILLS:
        planned_table = "\n".join(
            [
                "| Planned Skill | Status | Focus |",
                "| --- | --- | --- |",
                *[
                    f"| `{item['name']}` | {item['status']} | {item['focus']} |"
                    for item in PLANNED_SKILLS
                ],
            ]
        )
        planned_section = f"\n### Planned skills\n\n{planned_table}\n"

    return f"""# AIPE — Simulation Skills

AIPE Simulation Skills is the simulation workflow collection of **AI for Power Engineering**. It pairs
{len(rows)} agent skills - procedural `SKILL.md` workflows for circuit, control, CAD, PCB and field-analysis
tools - with an installable Python package, `aipe_simulation`, that executes real ngspice experiments and
analyses the resulting waveforms. Open-source tools (ngspice, python-control, FreeCAD, KiCad, Gmsh/Elmer)
are the default path; LTspice, PLECS, MATLAB/Simulink, SIMetrix/SIMPLIS, ANSYS and COMSOL remain optional,
externally licensed integrations. Contracts come from AIPE-Core; the manifest is indexed by AIPE-Registry.

## Features

- {len(rows)} skills with maturity and tool-access classification in `skills.json`; procedures live in each
  skill's `references/`. A skill is a written procedure for an agent: only the ngspice and python-control
  skills are backed by code that this repository executes
- `aipe_simulation.ngspice`: locates and qualifies ngspice, runs batch netlists, parses raw files
- `aipe_simulation.dab`: typed `DabCircuitSpec`, single-phase-shift gating, ideal (Level 1) and behavioural
  (Level 2) dual-active-bridge netlists, runner writing netlist, log, raw data, HDF5 waveforms and
  `summary.json`
- `aipe_simulation.waveforms`: HDF5 waveform dataset, steady-state detection, RMS/peak/power metrics,
  per-switch turn-off currents, ZVS conditions, volt-second and energy balances
- `aipe_simulation.control`: host-side single-phase-shift control baseline verified against ngspice runs
- Deterministic README generation and skill validation enforced in CI

## Installation

Python 3.10 or newer; numpy, h5py and PyYAML are installed with the package. Executing a simulation needs
ngspice on `PATH` (`sudo apt-get install ngspice` on Ubuntu, or the official Windows build with
`AIPE_NGSPICE` pointing at `ngspice_con.exe`); without it the solver tests skip. The open control example
needs `pe-python-control-analysis/requirements.txt`. No vendor software, device model or library is bundled:
a skill that names LTspice, PLECS, MATLAB/Simulink, SIMetrix/SIMPLIS, ANSYS or COMSOL needs your own
installation and licence of that tool.

```sh
python -m pip install -e ".[dev]"
python -m pip install -r pe-python-control-analysis/requirements.txt
```

## Usage

```sh
aipe-sim doctor                                   # locate and numerically qualify ngspice
aipe-sim dab run --analytic-start --out runs/dab-level1   # ideal 10 kW DAB: netlist, ngspice run, HDF5 waveforms, summary.json
python pe-python-control-analysis/scripts/buck_control.py --output buck-result.json
python -m pytest -q tests/                        # solver tests skip when ngspice is absent
```

`aipe-sim dab run` exits 0 only for a valid periodic steady state (1: solver failed, 2: completed but not
valid). Without `--analytic-start` the default circuit starts from zero current and needs about 130 cycles
(`--cycles 130`) to settle. The layout of `waveforms.h5` is specified in
[docs/waveform-dataset.md](docs/waveform-dataset.md).

To use a skill in Codex, copy its folder into your skills directory and invoke it by name, for example
`Use $pe-ngspice-switching-validation to check this switching netlist`; see
[docs/development.md](docs/development.md).

## Skill catalogue

{active_table}
{planned_section}
## Project Information

- Version: {version} (`pyproject.toml`, package `aipe-simulation-skills`)
- Status: Alpha (package classifier `Development Status :: 3 - Alpha`; `aipe.yaml` maturity `usable`).
  CAD, PCB and FEA skills are scaffolds, MCP connectors are evaluated only, no hardware validation is claimed
- Developer: Fulong Li
- Organisation: Spirit Connect / AIPE Labs
- License: MIT ([LICENSE](LICENSE)). Third-party tools and vendor device models keep their own licences and
  are not part of this repository
- Repository: <https://github.com/AIPE-Labs/AIPE-Simulation-Skills> · [Changelog](CHANGELOG.md)

## Documentation

- [Using and adding skills, conventions, README regeneration and CI](docs/development.md)
- [Architecture: package modules, skill layout and CLI](docs/architecture.md)
- [Executed 10 kW DAB benchmark and model lessons](docs/dab-models.md) ·
  [SPS control specification](docs/dab-sps-control-spec.md)
- [Waveform dataset format (`waveforms.h5`)](docs/waveform-dataset.md)
- [Validation record: what has been executed, where, and how to repeat it](docs/validation.md)
- [Tool policy and capability matrix](docs/tool-policy.md) · [Core mapping](docs/core-mapping.md) ·
  [Review of November 2026: open problems and proposals](docs/review-2026-11.md)
- [Skill metadata](skills.json) · [Capability manifest](aipe.yaml)
"""


def main() -> None:
    README.write_text(generate(), encoding="utf-8")


if __name__ == "__main__":
    main()
