# Reproducibility

## Requirements

The implementation-testing experiments were evaluated on Linux
x86_64 using Python 3.12.14 and GCC 13.3.0. No third-party Python
packages are required. Rodin and ProB are needed only for formal
model analysis.

## Controller experiment

Run from the repository root:

```bash
python3 experiments/controller/run_experiment.py
python3 scripts/verify_results.py --controller-run
```

The runner compiles the C controller using C11 with `-O2` and
regenerates tests, reference checks, mutation results, and
first-failure witnesses.

Expected results are 31 reachable core states, 372 transition
targets, 1,116 tests, and 18,216 cycle executions. The unmutated
controller produces no test failures. The complete suite detects
all 12 injected faults; stable-input tests detect ten. An additional
53,568 reference-only target-schedule runs produce no mismatch.
Compare these counts rather than elapsed time.

Inputs are encoded as `[engine, hazard, direction]`, with Boolean
values 0/1 and direction values neutral=0, left=1, and right=2.
Outputs are `[left, right]`, with levels 0/100. Core states are
`[mode, on, remaining]`, with mode values none=0, left=1,
right=2, and both=3.

The oracle reads command and lamp tables from Event-B XML and
uses a manually transcribed transition relation. Coverage concerns
the finite core projection, not the full refined event graph.

## External experiment

Run:

```bash
python3 experiments/external/experiment.py
python3 scripts/verify_results.py --external-run
```

The first execution downloads two public benchmark archives and
verifies their pinned SHA-256 hashes. The runner uses the supplied
DOT Mealy models directly and compiles the C implementations using
C99 with `-O0 -fwrapv`.

Eight model–implementation pairs are screened. The recorded
experiment accepts `m183` and `m159`, producing 973 tests and
6,093 input steps without reference-output mismatches. These tests
detect 45 of 59 compilable source mutants; 14 survive. The mutation
score is 76.27%, without excluding potentially equivalent mutants.
The other six pairs are excluded from mutation scoring because
their reference outputs differ from the model predictions.

Test ordering is deterministic. Mutation-site selection uses seed
20261002 plus the model's zero-based position in the screening list.
Each test stops at the first error output, and mutant evaluation
stops at the first detecting test. Surviving mutants have not been
independently classified as equivalent.

This experiment evaluates sequence generation and fault detection,
not Event-B extraction or within-cycle sampling semantics.

## Rodin

Use Rodin 3.9 and select:

File > Import > General > Existing Projects into Workspace

Import `models/AutomotivePilot`. The context is
`C_AutomotivePilot`, and the machines are `M0_AtomicCycle` and
`M1_SampledCycle`. They instantiate the generic modeling scheme
presented in the paper.

The recorded proof status is 67 discharged obligations out of 89:
25/32 for M0 and 42/57 for M1. The remaining 22 obligations are
pending. Saved proofs may be rebuilt or replayed on import.

`tools/rodin-headless/` contains research-runner sources and OSGi
metadata. Building requires Java 17 and Rodin's plugin JARs.
Recorded logs and obligation information are under `results/formal/`.

## ProB

Install ProB 1.16.1 and Java with support for source-file launching.
Run:

```bash
python3 tools/prob/run_prob.py /absolute/path/to/ProB
```

The installation directory must contain `probcli` and
`lib/probcliparser.jar`. The restricted Java exporter produces
executable representations from native Event-B XML. Its correctness
has not been formally established.

Model checking uses integer bounds MININT=-1000 and MAXINT=1000.
Recorded results are:

| Machine | States | Transitions |
|---|---:|---:|
| M0_AtomicCycle | 1,010 | 24,194 |
| M1_SampledCycle | 25,202 | 327,602 |

Both finite representations were completely explored without
reported invariant violations, deadlocks, or remaining open states.
State counts include initialization/setup states.

Rerun logs and results are written under `tools/prob/`.

## Recorded evidence

`results/` contains the recorded experimental results, generated
tests, witnesses, and formal-tool logs. Rerunning experiments writes
new outputs under `experiments/` or `tools/prob/`, preserving the
recorded results.

Archive and model hashes support source identification.
`SHA256SUMS.json` lists SHA-256 hashes for the packaged files and
can be used to check their integrity.

Passing the generated tests establishes agreement on the tested
executions; it does not prove implementation correctness.
