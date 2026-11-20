# Does age predict unscheduled removals? Data and code for reproducibility

Replication package for the manuscript

> Antonio C. P. Mesquita, *Does Age Predict Unscheduled Removals?*, submitted to *Reliability Engineering & System Safety*.

It contains the anonymised maintenance records of a fleet of 24 offshore helicopters (January 2024 – March 2026), the analysis code, the protocols and amendments fixed before each analysis, and the derived outputs behind every table and reported number.

## Contents

| Path | Content |
|---|---|
| `data/anonymised/` | Anonymised operator extracts: `hours_flown.csv` (daily flight hours and take-offs), `removals.csv` (part removals), `OMTH_tasks.csv` (executed maintenance tasks) and `anonymisation_log.json` (counts of replaced cells) |
| `config/` | Rotor-head inspection map, time-scale map of the hierarchical analysis, dimensionless cost parameters |
| `analysis/` | Analysis scripts, protocols (`preregistro_*.md`), amendments (`emenda_*.md`) and execution reports (`*_report.md`, in Portuguese) |
| `analysis/audit/` | Archived code versions and initial hash manifests used by the verification tests |
| `data/derived/` | Derived outputs, configurations, hash manifests and verification records of each analysis |
| `solver/paths.py` | Path resolution anchored to the repository root |
| `tests/` | `unittest` suite |

## Data and anonymisation

The data owner authorised publication of the records once anonymised. Before release:

- aircraft registrations are replaced by fixed codes `AC-01` to `AC-24`, in the identifier columns and in free text, and the airframe serial number is removed;
- locations and work centres are replaced by codes `LOC-xx`; place names and offshore installations in free text by `[LOCATION]` and `[INSTALLATION]`;
- technicians' names and the "Removed By" field are replaced by codes `P-xxx`, licence numbers are removed, and personal names in free text are replaced by `[PERSON]`;
- company names (operators, customers, manufacturers and suppliers) in free text and task codes are replaced by `[COMPANY]`, and e-mail addresses by `[EMAIL]` (applied to this public copy; see *Public adaptations*).

Part numbers, part names, aircraft model and document numbers are kept. The raw extracts and the re-identification maps are not distributed.

The outcome studied is a *recorded unscheduled removal* (reason `DISCREPANCY`), not necessarily a confirmed functional failure.

## Environment

Tested on Linux x86_64 (Intel Core i7-9700F, 8 logical cores, 32 GB) with Python 3.14.0. Exact package versions are pinned in `requirements-lock.txt`; `python-mip` bundles the open-source CBC solver, so no commercial licence is needed.

```bash
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-lock.txt
.venv/bin/python -m unittest discover -s tests      # full suite
```

All paths are resolved from the repository root, so scripts can be run from any directory. Random seeds are fixed in the protocols and stored in each configuration file.

## Reproducing the results

| Manuscript element | Command | Main outputs | Expected time |
|---|---|---|---|
| Section 3 (records, cohort, visits) | `python analysis/feasibility.py` | `analysis/feasibility_report.md`, `data/derived/spells.csv`, `data/derived/stoppages.csv` | seconds |
| Pipeline up to the pre-registered validation (A5) | `python analysis/run_all.py` | `data/derived/*.csv`, `data/derived/a5/`, `data/derived/pipeline_manifest.json` | about 1 min |
| Table K1 (RQ1) | included in `run_all.py` (`round2_survival.py`) | `data/derived/round2_weibull_fits.csv`, `data/derived/k1_candidates.csv` | — |
| Table K2, pre-registered A5 (RQ2) | included in `run_all.py` (`a5_validation.py`) | `data/derived/a5/decision.csv`, `data/derived/a5/` | — |
| Table K2, hierarchical A4 (RQ2) | `python analysis/a4_validation.py`; check with `python analysis/a4_verify.py` | `data/derived/a4/` | not recorded |
| Table K2, exposure erratum (RQ2) | `python analysis/errata_exposicao.py --workers 6` | `data/derived/a5_errata/`, `data/derived/a4_errata/` | about 3 min for the A4 erratum with 6 workers |
| Generator validation (RQ3) | `python analysis/a16_generator.py --validate` | `data/derived/a16/generator/` | not recorded |
| Type I error and power (RQ3) | `python analysis/a16_flow17.py --run --workers 6` (check: `--verify`) | `data/derived/a16/flow17/` | about 5 h with 6 workers |
| Calibration check (RQ4) | `python analysis/amendment015_runner.py`, then `python analysis/amendment015_authorised_verification.py` | `data/derived/a9/amendment015/references/`, `verification_table.csv` | exact references: more than 30 h |
| Profiling table (RQ4) | `python analysis/amendment015_authorised_profile.py` | `data/derived/a9/amendment015/profile/` | 3 h (safeguard) |

The expensive steps write checkpoints and can be resumed. The derived outputs in this repository allow every reported number to be checked without rerunning them. Bootstrap intervals use the aircraft as resampling unit (B = 10 000 in A5 and A4, B = 999 within each power-analysis replicate).

## Validation of this package

On 20 November 2026 a fresh clone of this repository was validated in a new virtual environment built from `requirements-lock.txt` (Python 3.14.0, Linux):

- `python -m unittest discover -s tests`: 206 tests, OK (4 skipped, see below);
- `python analysis/run_all.py` (about 3 min): all 12 steps completed. Numerical outputs matched the distributed ones within `numpy.isclose(atol=1e-8, rtol=1e-6)`, with identical categorical values, signs and decisions (`data/derived/a5/decision.csv` byte-identical); the distributed outputs were produced on Windows, and the differences are floating-point differences between platforms (largest relative difference in fitted parameters below 1e-7). Five outputs differ otherwise, as expected from the masking described below: `recurrent_tasks.csv` and `task_labour_ledger.csv` only in row order, and `task_removal_labour_links.csv`, `extended_review_results.csv` and `removal_review_evidence.csv` only in their text-hash columns.

## Public adaptations

This package was assembled from the private working repository. Differences from that repository:

- In `data/anonymised/`, 41 e-mail addresses were replaced by `[EMAIL]` and company names by `[COMPANY]` (30 638 replacements in `Task #`, `Task Description`, `Sign Off Remarks`, `Removal Remarks` and part descriptions; no two distinct task codes or task descriptions became identical). The same masking was applied to the distributed derived outputs and reports (454 replacements, all in task names). The SHA-256 of `OMTH_tasks.csv` and `removals.csv` therefore differ from the input hashes recorded in the historical manifests.
- The manual decisions of the documentary review (`analysis/removal_review_decisions.csv`, `analysis/extended_review_decisions.csv`) are keyed by the SHA-256 of the source text read by the reviewer. For the 12 sources whose text changed only by the `[COMPANY]` masking, the keys were replaced by the hashes of the masked text (19 keys); the decisions themselves are unchanged. Regenerated review outputs therefore differ from the distributed ones only in the text-hash columns.
- `analysis/run_all.py` checks only the protected files that are distributed (the manuscript is not) and records `not a git checkout` when run outside Git.
- Four tests that require the manuscript, the private project documents or the private Git history are skipped (`PRIVATE_REPOSITORY` guard).
- Not distributed: the manuscript and bibliography, private project documents, the raw extracts and identifier maps, the anonymisation script (it contains the confidential location dictionary), the machine-transfer archives, `data/derived/a4/bootstrap.csv` (51 MB, regenerated by `a4_validation.py`) and legacy synthetic-data code unrelated to the manuscript.
- Execution logs keep the absolute paths of the machines on which they were produced.

## Licence

Data, derived outputs, documentation and code are licensed under the Creative Commons Attribution 4.0 International licence (`LICENSE`).

## Citation

If you use these data or code, please cite the article once published; the citation will be added here.
