# Reproducibility

## Controller experiment

Run from the repository root: `python3 experiments/controller/run_experiment.py`.
It regenerates tests, reference checks, mutant results, and witnesses. Compare numerical counts rather than elapsed time. Input encoding: `[engine,hazard,direction]`, booleans 0/1, direction neutral=0,left=1,right=2; outputs are `[left,right]` with levels 0/100. Core state is `[mode,on,remaining]` with mode none=0,left=1,right=2,both=3.

## External experiment

Run `python3 experiments/external/experiment.py`. First execution downloads two archives and verifies their pinned hashes. Test order is deterministic; mutation site selection uses seed 20261002 plus model position in the eight-model screening list. The runner stops at the first error output and at the first killing test for each mutant. Survivors are not independently classified as equivalent.

## Rodin

Use Rodin 3.9: File > Import > General > Existing Projects into Workspace; select `models/AutomotivePilot`. Saved proof files may be rebuilt/replayed on import. Machine names are `M0_AtomicCycle` and `M1_SampledCycle`; the context is `C_AutomotivePilot`. These instantiate the generic cyclic modeling scheme shown in the manuscript. The recorded status is 67/89, not a fully proved development.

`tools/rodin-headless/` contains research runner sources and OSGi metadata, not an installable GUI plugin. Building requires Java 17 and Rodin's plugin JARs. Historical logs and detailed obligations are under `results/formal/`.

## ProB

Install ProB 1.16.1 and Java (source-file launcher). Run:

```bash
python3 tools/prob/run_prob.py /absolute/path/to/ProB
```

The installation directory must contain `probcli` and `lib/probcliparser.jar`. The restricted Java exporter creates executable representations from the native model XML; exporter correctness is not formally established. Bounds are MININT=-1000 and MAXINT=1000. Logs and results are written under `tools/prob/`. Rodin/ProB are not required for the controller or external test runners.

## Recorded evidence

`results/` preserves the earlier evaluated configuration; rerun outputs live under `experiments/` or `tools/prob/`. Formal tools and external source downloads have not been rerun during packaging. Archive and model hashes permit source comparison; SHA256SUMS.json checks the packaged files.
