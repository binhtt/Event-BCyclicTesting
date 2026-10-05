"""Re-export and exhaustively check the finite pilot with ProB 1.16.1."""
import json
import re
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parent
installation=Path(sys.argv[1]).resolve()
cli=installation/'probcli'
parser=installation/'lib/probcliparser.jar'
results=[]
for name in ('M0_AtomicCycle','M1_SampledCycle'):
    destination=root/'models'/f'{name}.eventb'
    subprocess.run(['java','--class-path',str(parser),str(root/'ExportForProB.java'),str(root/'models'),name,str(destination)],check=True)
    command=[str(cli),str(destination),'-p','MAXINT','1000','-p','MININT','-1000',
             '-pref_group','model_check','unlimited','-model_check','-c',
             '-logxml',str(root/'logs'/f'{name}.xml')]
    proc=subprocess.run(command,capture_output=True,text=True,timeout=180)
    output=proc.stdout+proc.stderr
    (root/'logs'/f'{name}.log').write_text(output)
    complete='No counter example found. ALL states visited.' in output
    passed=proc.returncode==0 and complete and not re.search(r'Total Errors: [1-9]',output)
    stats={}
    for key in ('STATES','TOTAL_TRANSITIONS','deadlocked','invariant_violated','invariant_not_checked','open'):
        match=re.search(r'^'+key+r'\s+(\d+)\s*$',output,re.M)
        if match: stats[key]=int(match.group(1))
    passed=passed and all(stats.get(key)==0 for key in ('deadlocked','invariant_violated','invariant_not_checked','open'))
    results.append(dict(machine=name,command=command,exit_code=proc.returncode,exhaustive_complete=complete,passed=passed,statistics=stats))
    print(name,stats,'PASS' if passed else 'INCOMPLETE OR FAILED')
(root/'prob_results.json').write_text(json.dumps(results,indent=2)+'\n')
if not all(r['passed'] for r in results): raise SystemExit(1)
