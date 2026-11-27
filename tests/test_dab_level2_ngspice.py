"""Executed Level 2 (behavioural) DAB run and the waveform-dataset contract (pytest marker: solver).

The specification in ``tests/data/dab-10kw-level2-spec.json`` is the one the AIPE-Workflows 10 kW
dual-active-bridge example hands to ``run_dab`` (task ``circuit-sim-level2``, AIPE-Workflows commit
6284f18). The reference numbers below are the result recorded there on 2026-10-21 with ngspice 47 on
Windows 11. This test repeats that run with whatever ngspice is installed (ngspice 42 on the Ubuntu CI
runner), so the cross-platform, cross-version agreement is checked on every push instead of asserted.

It also pins the layout of ``waveforms.h5`` that downstream packages read: format tag, channel names,
units and metadata keys. Extending the dataset is allowed; removing or renaming is a breaking change.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import h5py
import pytest

from aipe_simulation.dab.gating import SWITCHES
from aipe_simulation.dab.run import DabRunResult, run_dab
from aipe_simulation.dab.spec import DabCircuitSpec
from aipe_simulation.ngspice.locate import locate_ngspice
from aipe_simulation.waveforms.dataset import FORMAT, WaveformDataset

pytestmark = pytest.mark.solver

SPEC_FILE = Path(__file__).parent / "data" / "dab-10kw-level2-spec.json"
SPEC_SHA256 = "57052e6938b4a5d09ee66e9a3645903914e0fd9da458edde3cee7c8b874fc49e"
NETLIST_SHA256 = "e04c677d3c6b185b56dd45d4be526cf68f9fd266b12b201bb8731c5ff33939bb"
# Recorded with ngspice 47 / Windows 11 (AIPE-Workflows examples/dab-10kw/results/circuit-sim-level2).
RECORDED = {"p_in_W": 9694.201837231883, "p_out_W": 9607.834640398823, "loss_W": 131.657989873343,
            "i_L_rms_A": 13.29969726550158, "v_dc2_V": 392.0772117527901}

# The contract downstream readers rely on.
CHANNEL_UNITS = {
    **{name: "V" for name in ("v_a", "v_b", "v_c", "v_d", "v_dc1", "v_dc2", "v_ab", "v_cd", "v_cd_ref", "v_tp", "v_ts", "v_L")},
    **{name: "A" for name in ("i_L", "i_m", "i_s", "i_p_ideal", "i_dc1", "i_dc2")},
    "p_1": "W", "p_2": "W",
    **{f"i_{s}": "A" for s in SWITCHES}, **{f"v_ds_{s}": "V" for s in SWITCHES}, **{f"g_{s}": "V" for s in SWITCHES},
}
METADATA_KEYS = {"conventions", "created_at", "format_note", "netlist_sha256", "producer", "solver", "spec",
                 "spec_sha256", "switches", "timing"}
SUMMARY_KEYS = {"bridges", "conventions", "dataset_sha256", "energy_balance", "numerical", "ports", "run", "schema",
                "series_path", "spec_sha256", "status", "steady_state", "switches", "symmetry", "transformer", "valid",
                "window", "zvs_overview"}


def rel_err(actual: float, expected: float) -> float:
    return abs(actual - expected) / abs(expected)


@pytest.fixture(scope="module")
def ngspice():
    info = locate_ngspice()
    if info is None:
        pytest.skip("ngspice not found (set AIPE_NGSPICE or AIPE_TOOLS_DIR)")
    return info


@pytest.fixture(scope="module")
def level2_run(ngspice, tmp_path_factory) -> DabRunResult:
    spec = DabCircuitSpec.from_dict(json.loads(SPEC_FILE.read_text(encoding="utf-8")))
    return run_dab(spec, tmp_path_factory.mktemp("dab_level2"), ngspice=ngspice)


def test_fixture_is_the_recorded_workflows_specification():
    spec = DabCircuitSpec.from_dict(json.loads(SPEC_FILE.read_text(encoding="utf-8")))
    assert spec.level == 2 and spec.validate() == []
    assert spec.sha256() == SPEC_SHA256


def test_level2_netlist_is_byte_identical_to_the_recorded_run(level2_run):
    assert level2_run.spec_sha256 == SPEC_SHA256
    assert level2_run.run["netlist_sha256"] == NETLIST_SHA256


def test_level2_reaches_steady_state_and_matches_the_recorded_result(level2_run):
    r = level2_run
    assert r.succeeded is True and r.valid is True and r.status == "steady_state", r.messages
    ports, series = r.summary["ports"], r.summary["series_path"]
    assert rel_err(ports["port1"]["power_avg"]["value"], RECORDED["p_in_W"]) < 1e-3
    assert rel_err(ports["port2"]["power_avg"]["value"], RECORDED["p_out_W"]) < 1e-3
    assert rel_err(series["i_L_rms"]["value"], RECORDED["i_L_rms_A"]) < 1e-3
    assert rel_err(ports["port2"]["voltage_avg"]["value"], RECORDED["v_dc2_V"]) < 1e-3
    # The loss is a small difference of two large powers, so it is the quantity most sensitive to the solver version.
    assert rel_err(ports["loss_total"]["value"], RECORDED["loss_W"]) < 0.03
    assert r.summary["steady_state"]["periodicity_error"] < 1e-2


def test_waveform_dataset_contract(level2_run):
    path = Path(level2_run.dataset_path)
    with h5py.File(path, "r") as handle:
        assert handle.attrs["format"] == FORMAT == "aipe-waveform-dataset/0.1"
        assert set(handle.keys()) == {"time", "channels"}
        assert handle["time"].dtype == "float64" and handle["time"].attrs["unit"] == "s"
        assert METADATA_KEYS <= set(json.loads(handle.attrs["metadata"]))
        channels = handle["channels"]
        missing = set(CHANNEL_UNITS) - set(channels.keys())
        assert not missing, f"channels removed from the dataset: {sorted(missing)}"
        for name, unit in CHANNEL_UNITS.items():
            assert channels[name].dtype == "float64" and channels[name].shape == handle["time"].shape, name
            assert channels[name].attrs["unit"] == unit, name
            assert {"description", "sign_convention"} <= set(channels[name].attrs), name
        assert handle.attrs["sha256"] == level2_run.dataset_sha256
    dataset = WaveformDataset.load_hdf5(path)
    assert dataset.sha256() == level2_run.dataset_sha256
    assert dataset.metadata["producer"]["id"] == "aipe.simulation-skills.dab"
    assert SUMMARY_KEYS <= set(level2_run.summary)


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "aipe_simulation.cli", *args], capture_output=True, text=True, timeout=300)


def test_cli_analytic_start_gives_a_valid_run_and_exit_code_zero(ngspice, tmp_path):
    cp = _cli("dab", "run", "--analytic-start", "--out", str(tmp_path / "run"), "--ngspice", ngspice.path)
    assert cp.returncode == 0, cp.stdout + cp.stderr
    brief = json.loads(cp.stdout)
    assert brief["valid"] is True and brief["status"] == "steady_state"
    assert rel_err(brief["p_out_W"], 10_000.0) < 1e-2
    spec = json.loads((tmp_path / "run" / "spec.json").read_text(encoding="utf-8"))
    assert spec["sim"]["initial_series_current"] == pytest.approx(14.285714285714288, rel=1e-12)


def test_cli_exit_code_two_when_the_run_is_not_a_steady_state(ngspice, tmp_path):
    # Zero-state start with the default 20 mOhm damping needs far more than 6 cycles.
    cp = _cli("dab", "run", "--cycles", "6", "--out", str(tmp_path / "run"), "--ngspice", ngspice.path)
    assert cp.returncode == 2, cp.stdout + cp.stderr
    brief = json.loads(cp.stdout)
    assert brief["succeeded"] is True and brief["valid"] is False and brief["status"] == "not_steady_state"
