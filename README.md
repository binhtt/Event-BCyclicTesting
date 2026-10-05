# Event-B-Based Testing of Cyclic Reactive Systems

Research artifact for the article by Thanh-Binh Trinh and Ninh-Thuan Truong.

The workflow combines a finite executable controller model, transition-directed test sequences, controlled input changes between cycle stages, and output checks. It includes an automotive turn-signal and hazard-light case study and a separate ASML/RERS 2019 benchmark experiment.

## Requirements and quick start

Linux, Python 3 (evaluated with 3.12.14), and GCC (evaluated with 13.3.0). No third-party Python packages are required.

```bash
python3 experiments/controller/run_experiment.py
python3 scripts/verify_results.py --controller-run
```

The controller runner compiles C11 with `-O2` and writes outputs beside the script. The checked-in historical results are preserved separately under `results/`.

To run the external experiment (network access to download pinned public archives is required):

```bash
python3 experiments/external/experiment.py
python3 scripts/verify_results.py --external-run
```

External C is compiled with `-std=c99 -O0 -fwrapv`. The script screens all eight pairs and mutates only pairs passing reference checks. Generated sources, libraries, and downloaded archives are excluded from version control.

## Recorded results

| Experiment | Tests | Execution steps | Detection |
|---|---:|---:|---|
| Controller | 1,116 | 18,216 cycles | 12/12 deliberately injected faults |
| External accepted pairs | 973 | 6,093 inputs | 45/59 source mutants (76.27%) |

Controller: 31 reachable core states, 372 transition targets, three schedules per target. Stable-input tests detect 10/12 faults; updates after Sample detect 11/12; updates in both gaps detect 12/12. The unmutated controller passes all tests. An additional 53,568 reference-only target-schedule runs show no mismatch.

External screening accepts `m183` and `m159`. Six other pairs show reference mismatches and are excluded from mutation scoring. Potentially equivalent mutants are retained in the denominator.

Rodin 3.9 discharged 67/89 proof obligations (22 pending). Recorded ProB 1.16.1 checks explored M0: 1,010 states/24,194 transitions; M1: 25,202 states/327,602 transitions, without reported invariant violations or deadlocks. These are historical tool results, not results of the quick-start command.

## Repository contents

- `models/AutomotivePilot/`: native Rodin context, machines, and saved proof data.
- `experiments/controller/`: Python oracle/test generator and procedural C controller with 12 selectable faults.
- `experiments/external/`: DOT/C benchmark retrieval, screening, and source-mutation runner.
- `results/`: recorded tests, witnesses, summaries, and formal-tool logs.
- `tools/`: restricted ProB exporter and Rodin headless proof-runner source.
- `docs/REPRODUCIBILITY.md`: execution and model-import details.
- `scripts/verify_results.py`: consistency checks against the article's reported counts.

## Scope

The controller oracle reads command/lamp tables from Event-B XML and uses a manually transcribed four-branch transition relation. It is not a general Event-B interpreter or automatic Event-B-to-test translator. The C controller is separately structured, but shared interpretation errors remain possible.

Coverage refers to 372 targets in the finite core, not the full M1 event graph. The synchronous harness observes publication checkpoints; it does not measure physical timing or concurrent execution. External experiments use supplied Mealy models directly and do not validate Event-B extraction or cyclic sampling semantics. Passing finite tests is not a correctness proof.

## Benchmark provenance and licensing

The controller is a newly constructed simplified pilot informed by SimB examples at commit `ebe94030c5e884431917e0eef18c6204af306a00`: https://github.com/favu100/SimB-examples . It is not a full translation of the original benchmark.

External sources: https://automata.cs.ru.nl/BenchmarkASMLRERS-YangEtAl2019/Description and https://rers-challenge.org/2019/index.php?page=industrialProblemsHead . Archives are pinned by SHA-256 in `experiments/external/sources.json`; upstream benchmark archives are not bundled. These are generated benchmark programs, not deployed production software.

No repository-wide redistribution license has been selected. Upstream materials remain subject to their respective terms.

## Citation

The article is a manuscript; no journal or DOI is claimed here. Cite the title and authors above and the specific repository commit or release used.
