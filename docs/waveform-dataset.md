# Waveform dataset format (`waveforms.h5`)

Every executed run writes its waveforms to one HDF5 file. Other AIPE packages (magnetics design, device
loss evaluation, thermal design, AIPE-Workflows) read this file, so its layout is a compatibility contract:
**channels and attributes may be added; none may be removed, renamed or change unit without a new format
tag.** `tests/test_dab_level2_ngspice.py::test_waveform_dataset_contract` fails if the contract is broken.

Format tag: `aipe-waveform-dataset/0.1` (constant `aipe_simulation.waveforms.dataset.FORMAT`).

## Layout

| Path | Type | Content |
| --- | --- | --- |
| attribute `format` | string | `aipe-waveform-dataset/0.1` |
| attribute `metadata` | JSON string | provenance, see below |
| attribute `sha256` | hex string | SHA-256 over the `time` bytes, then for every channel in name order the UTF-8 name and the data bytes (float64, native byte order) |
| `/time` | float64, gzip | time in seconds, attribute `unit = "s"`; non-uniform (the solver's own time points) |
| `/channels/<name>` | float64, gzip, same length as `/time` | attributes `unit`, `description`, `sign_convention` |

`WaveformDataset.load_hdf5` recomputes the hash and refuses a file whose content was modified.

## Channels written by the DAB runner

| Channels | Unit | Meaning |
| --- | --- | --- |
| `v_a`, `v_b`, `v_c`, `v_d` | V | leg mid-node voltages (A, B primary; C, D secondary) |
| `v_ab`, `v_cd`, `v_cd_ref` | V | bridge AC voltages; `v_cd_ref = n * v_cd` is referred to the primary |
| `v_dc1`, `v_dc2` | V | port 1 DC-link voltage, port 2 DC voltage |
| `v_tp`, `v_ts`, `v_L` | V | transformer primary and secondary terminal voltages, external inductor voltage |
| `i_L` | A | external series inductor current, from node `a` towards the transformer |
| `i_m` | A | magnetising current, primary referred |
| `i_s`, `i_p_ideal` | A | secondary current out of the transformer into node `c`; `i_p_ideal = i_s / n` |
| `i_dc1`, `i_dc2` | A | DC current into the converter from port 1; out of the converter into port 2 |
| `p_1`, `p_2` | W | instantaneous power entering from port 1; leaving into port 2 |
| `i_S1` ... `i_S8` | A | switch-pair (channel plus antiparallel diode) current, positive drain to source |
| `v_ds_S1` ... `v_ds_S8` | V | drain-source voltages |
| `g_S1` ... `g_S8` | V | gate signals |

Time origin: the centre of the primary positive half-cycle (S1 and S4 on). Phase shift `phi > 0` means the
secondary lags and power flows from port 1 to port 2. The same conventions are stored in the file.

## Metadata keys

`format_note`, `spec` (the complete `DabCircuitSpec`), `spec_sha256`, `timing` (gate timing), `switches`
(switch table), `solver` (`id`, `version`, `path`, `platform`, `command`), `netlist_sha256`, `created_at`
(UTC), `producer` (`id = "aipe.simulation-skills.dab"`, `version`), `conventions`.

`solver.path` and `solver.command` record where ngspice ran on the producing machine. They are provenance,
not something a reader should open.

## Reading it

```python
from aipe_simulation.waveforms.dataset import WaveformDataset

ds = WaveformDataset.load_hdf5("runs/dab-level1/waveforms.h5")   # verifies the hash
t, i_L = ds.time, ds.get("i_L")
print(ds.channels["i_L"].unit, ds.metadata["solver"]["version"])
```

Without this package, any HDF5 reader works (`h5py.File(path)["channels/i_L"][...]`).

## The summary next to it

`summary.json` (schema tag `aipe-dab-waveform-summary/0.1`) holds the quantities derived from the steady-state
window: `ports`, `series_path`, `transformer`, `switches`, `bridges`, `zvs_overview`, `energy_balance`,
`symmetry`, `steady_state`, `numerical`, `window`, plus `valid`, `status`, `spec_sha256` and `dataset_sha256`.
A result is usable only when `valid` is `true`; `status` then reads `steady_state`.
