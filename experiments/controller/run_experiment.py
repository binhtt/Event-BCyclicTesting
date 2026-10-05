"""Pilot MBT: finite relation transcription + XML tables vs independent C SUT.
Not a general Event-B interpreter; not a native ProB test generator.
"""
from pathlib import Path
from itertools import product
from collections import deque
import ctypes as ct
import xml.etree.ElementTree as ET
import json, re, subprocess, time, hashlib

ROOT=Path(__file__).resolve().parent
INPUTS=list(product((0,1),(0,1),range(3)))
INITIAL=(0,0,0)
TOKENS={'FALSE':0,'TRUE':1,'pNeutral':0,'pLeft':1,'pRight':2,
        'noMode':0,'leftMode':1,'rightMode':2,'bothMode':3,'0':0,'100':100}

def load_tables():
    axioms={e.get('org.eventb.core.label'):e.get('org.eventb.core.predicate')
            for e in ET.parse(ROOT/'models/C_AutomotivePilot.buc').getroot()
            if e.tag=='org.eventb.core.axiom'}
    tables={}
    for name in ('command','lampL','lampR'):
        pred=next(v for v in axioms.values() if v.startswith(name+' = {'))
        entries=pred.split('{',1)[1].rsplit('}',1)[0].split(',')
        table={}
        for entry in entries:
            flat=entry.replace('(','').replace(')','')
            values=tuple(TOKENS[t.strip()] for t in flat.split('↦'))
            table[values[:-1]]=values[-1]
        tables[name]=table
    assert len(tables['command'])==12
    assert len(tables['lampL'])==len(tables['lampR'])==8
    return tables

TABLES=load_tables()

def step(old,inp):
    """Enumerate the four disjuncts in Cycle's transition relation."""
    a,on,n=old;m=TABLES['command'][tuple(inp)]
    candidates=[]
    for b,r in product(range(2),range(5)):
        if ((m==0 and b==0 and r==0) or
            (m!=0 and a==0 and b==1 and r==4) or
            (m!=0 and a!=0 and n>0 and b==on and r==n-1) or
            (m!=0 and a!=0 and n==0 and b==1-on and r==4)):
            candidates.append((m,b,r))
    assert len(candidates)==1
    return candidates[0]

def lamps(state):
    key=tuple(state[:2]);return (TABLES['lampL'][key],TABLES['lampR'][key])

class Controller(ct.Structure):
    _fields_=[(x,ct.c_int) for x in ('mode','on','count','left','right')]

def schedules(inp):
    e,h,p=inp
    return [('stable',inp,inp),
            ('after_sample',(1-e,1-h,(p+1)%3),inp),
            ('both_gaps',(1-e,1-h,(p+1)%3),(1-e,1-h,(p+2)%3))]

def main():
    t=time.perf_counter()
    subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',
                    str(ROOT/'controller.c'),'-o',str(ROOT/'controller.so')],check=True)
    lib=ct.CDLL(str(ROOT/'controller.so'))
    lib.reset.argtypes=[ct.POINTER(Controller)]
    lib.cycle.argtypes=[ct.POINTER(Controller)]+[ct.c_int]*10
    lib.cycle.restype=ct.c_int
    paths={INITIAL:[]};queue=deque([INITIAL]);edges=[]
    while queue:
        old=queue.popleft()
        for inp in INPUTS:
            new=step(old,inp);edges.append((old,inp,new))
            if new not in paths:paths[new]=paths[old]+[inp];queue.append(new)
    cases=[]
    for index,(old,inp,new) in enumerate(edges):
        for profile,noise1,noise2 in schedules(inp):
            # Ten suffix cycles expose hidden countdown faults at lamp outputs.
            sequence=paths[old]+[inp]+[inp]*10
            oracle=[];state=INITIAL
            for sample in sequence:state=step(state,sample);oracle.append(lamps(state))
            cases.append({'id':f'T{index:03}_{profile}','target_source':old,
                          'target_input':inp,'target_destination':new,
                          'target_cycle':len(paths[old]),'inputs':sequence,
                          'noise_after_sample':noise1,'noise_after_decide':noise2,
                          'expected_outputs':oracle})
    (ROOT/'generated_tests.json').write_text(json.dumps(cases,separators=(',',':')))
    bug_names=['reference','short_phase_4','long_phase_6','direction_over_hazard',
               'engine_blocks_hazard','reset_on_mode_change','read_live_at_decide',
               'read_live_at_emit','publish_at_decide','swap_lamps',
               'use_previous_mode_for_output','ignore_hazard','hazard_right_dark']
    def execute(case,bug):
        sut=Controller();lib.reset(ct.byref(sut))
        for k,(inp,expected) in enumerate(zip(case['inputs'],case['expected_outputs'])):
            a,b=(case['noise_after_sample'],case['noise_after_decide']) if k==case['target_cycle'] else (inp,inp)
            early=lib.cycle(ct.byref(sut),*inp,*a,*b,bug)
            actual=(sut.left,sut.right)
            if early or actual!=tuple(expected):
                return {'cycle':k,'sample':inp,'after_sample':a,'after_decide':b,
                        'expected':expected,'actual':actual,'early_output':bool(early)}
        return None
    outcomes=[];witnesses=[]
    for bug,name in enumerate(bug_names):
        fails=0;first=None;profiles={p:0 for p in ('stable','after_sample','both_gaps')}
        for case in cases:
            mismatch=execute(case,bug)
            if mismatch:
                fails+=1
                profile=case['id'].split('_',1)[1];profiles[profile]+=1
                if first is None:first={'mutant':name,'test_id':case['id'],
                                       'test':case,'mismatch':mismatch}
        outcomes.append({'mutant':name,'failed_tests':fails,'total_tests':len(cases),
                         'failed_tests_by_profile':profiles})
        if first:witnesses.append(first)
    assert outcomes[0]['failed_tests']==0,outcomes[0]
    # Baseline only: all 12 x 12 noise pairs for every reachable core edge.
    exhaustive_count=0;exhaustive_fail=0
    for old,inp,new in edges:
        for a,b in product(INPUTS,repeat=2):
            sut=Controller();lib.reset(ct.byref(sut))
            for access in paths[old]:lib.cycle(ct.byref(sut),*access,*access,*access,0)
            early=lib.cycle(ct.byref(sut),*inp,*a,*b,0)
            exhaustive_count+=1
            exhaustive_fail+=bool(early or (sut.left,sut.right)!=lamps(new))
    assert exhaustive_fail==0
    killed=sum(x['failed_tests']>0 for x in outcomes[1:])
    result={'oracle':'Four-disjunct finite relation transcription; command/lamp tables parsed from Event-B XML',
            'sut':'Independent procedural C research pilot, compiled with gcc',
            'observable_oracle':'left/right lamps after Emit; no output update before Emit',
            'reachable_core_states':len(paths),'core_transition_targets':len(edges),
            'core_transition_target_coverage':1.0,'schedule_profiles':3,
            'generated_tests':len(cases),'suite_cycle_steps':sum(len(c['inputs']) for c in cases),
            'reference_failures':outcomes[0]['failed_tests'],
            'exhaustive_target_schedule_runs':exhaustive_count,'exhaustive_reference_failures':exhaustive_fail,
            'mutants':len(outcomes)-1,'killed_mutants':killed,'mutation_score':killed/(len(outcomes)-1),
            'stable_only_killed_mutants':sum(x['failed_tests_by_profile']['stable']>0 for x in outcomes[1:]),
            'mutant_results':outcomes[1:],'elapsed_seconds':round(time.perf_counter()-t,3),
            'scope':'Finite core projection of this pilot; not full M1 event graph coverage, native model execution or production-system evidence',
            'rodin_proof_status':{'closed':67,'total':89,'pending':22}}
    (ROOT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    (ROOT/'counterexamples.json').write_text(json.dumps(witnesses,indent=2)+'\n')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'models').iterdir()}
    (ROOT/'model_hashes.json').write_text(json.dumps(hashes,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
