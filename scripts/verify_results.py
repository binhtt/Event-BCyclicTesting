"""Verify paper counts in recorded or newly generated experiment results."""
import argparse, json
from pathlib import Path
r=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--controller-run',action='store_true')
p.add_argument('--external-run',action='store_true')
a=p.parse_args()
c=json.loads((r/('experiments/controller' if a.controller_run else 'results/controller')/'results.json').read_text())
for k,v in {'reachable_core_states':31,'core_transition_targets':372,'generated_tests':1116,'suite_cycle_steps':18216,'reference_failures':0,'mutants':12,'killed_mutants':12,'stable_only_killed_mutants':10,'exhaustive_target_schedule_runs':53568,'exhaustive_reference_failures':0}.items():
    assert c[k]==v,(k,c[k],v)
e=json.loads((r/('experiments/external' if a.external_run else 'results/external')/'results.json').read_text())
accepted=[m for m in e if m.get('mutation_status')=='completed']
assert len(e)==8 and len(accepted)==2
assert {m['benchmark'] for m in accepted}=={'m183','m159'}
assert sum(m['tests'] for m in accepted)==973
assert sum(m['input_steps'] for m in accepted)==6093
mutants=[x for m in accepted for x in m['mutants']]
assert len(mutants)==59
assert sum(x['status']=='killed' for x in mutants)==45
assert sum(x['status']=='survived' for x in mutants)==14
print('PASS: controller and external counts match the manuscript.')
