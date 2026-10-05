"""External DOT oracle vs instrumented original RERS C, with source mutants.
Input interface restricted to common mapped symbols. Stop on first error.
Requires the pinned sources.json beside this script.
Original-C replay with undefined-behavior instrumentation is a separate analysis.
"""
from pathlib import Path
from collections import deque,Counter
import zipfile,re,json,hashlib,subprocess,ctypes,random,time,urllib.request
ROOT=Path(__file__).resolve().parent
URLS={'source.zip':'https://automata.cs.ru.nl/pmwiki/uploads/BenchmarkASMLRERS-YangEtAl2019/challenge_and_training_set_with_dotfiles.zip',
      'code.zip':'https://rers-challenge.org/2019/problems/industrial/IndLtlCtlCodeRers2019_Mar_9th.zip'}
MODELS=['m183','m158','m164','m159','m135','m55','m54','m76']

def prepare():
    manifest_path=ROOT/'sources.json'
    if not manifest_path.exists():
        raise FileNotFoundError('sources.json is required to verify pinned benchmark archives')
    expected=json.loads(manifest_path.read_text())['archives']
    for name in URLS:
        if name not in expected:
            raise ValueError('Missing pinned hash for '+name)
    for name,url in URLS.items():
        if not (ROOT/name).exists():urllib.request.urlretrieve(url,ROOT/name)
        actual=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        if actual!=expected[name]:
            raise ValueError('Source archive changed: '+name)
    manifest=[]
    zd=zipfile.ZipFile(ROOT/'source.zip');zc=zipfile.ZipFile(ROOT/'code.zip')
    for model in MODELS:
        dest=ROOT/model;dest.mkdir(exist_ok=True)
        names=[(zd,next(n for n in zd.namelist() if n.endswith('/'+model+'.dot')))]
        names += [(zc,n) for n in zc.namelist() if f'/{model}/' in n and not n.startswith('__') and n.endswith(('.c','version.txt'))]
        for z,n in names:
            data=z.read(n);p=dest/Path(n).name;p.write_bytes(data)
            manifest.append({'model':model,'archive_entry':n,'file':str(p.relative_to(ROOT)),
                             'sha256':hashlib.sha256(data).hexdigest()})
    (ROOT/'sources.json').write_text(json.dumps({'urls':URLS,'archives':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in URLS},'files':manifest},indent=2))

def load(model):
    folder=ROOT/model;source=next(folder.glob('*.c')).read_text()
    mapping={a:int(b) for a,b in re.findall(r'^(\S+)\s+(\d+)\s*$',next(folder.glob('*version.txt')).read_text(),re.M)}
    dot=(folder/(model+'.dot')).read_text()
    initial=int(re.search(r'__start0\s*->\s*"(\d+)"',dot).group(1))
    edges={}
    for a,b,inp,out in re.findall(r'"(\d+)"\s*->\s*"(\d+)"\s*\[label="([^/"]+)/([^"\n]+)"\]',dot):
        edges[int(a),inp]=(int(b),out)
    cinputs=set(map(int,re.search(r'int inputs\[\]\s*=\s*\{([^}]+)',source).group(1).split(',')))
    alphabet=sorted({i for _,i in edges if i in mapping and mapping[i] in cinputs})
    return source,mapping,initial,edges,alphabet

def cases_for(initial,edges,alphabet):
    paths={initial:[]};q=deque([initial]);targets=[]
    while q:
        state=q.popleft()
        for inp in alphabet:
            if (state,inp) not in edges:continue
            nxt,out=edges[state,inp];targets.append((state,inp,nxt,out))
            if out!='error' and nxt not in paths:paths[nxt]=paths[state]+[inp];q.append(nxt)
    sequences=set()
    for state,inp,nxt,out in targets:
        base=paths[state]+[inp];sequences.add(tuple(base))
        if out!='error':
            for suffix in alphabet:sequences.add(tuple(base+[suffix]))
    cases=[]
    for seq in sorted(sequences,key=lambda s:(len(s),s)):
        state=initial;expected=[];actualseq=[]
        for inp in seq:
            nxt,out=edges[state,inp];expected.append(out);actualseq.append(inp);state=nxt
            if out=='error':break
        cases.append((actualseq,expected))
    return paths,targets,cases

def instrument(source,mapping,mutation=None):
    source=source[:source.index('int main()')]
    if mutation:
        start,end,new=mutation;source=source[:start]+new+source[end:]
    prefix=source[:source.index('void calculate_outputm1(int input)')]
    globals_=re.findall(r'^\s*int\s+(\w+)\s*=\s*(-?\d+)\s*;',prefix,re.M)
    # Numeric output capture preserves original transition code.
    source=re.sub(r'printf\("%d\\n",\s*(\d+)\);\s*fflush\(stdout\);',r'last_output=\1;',source)
    source=re.sub(r'fprintf\(stderr,\s*"Invalid input: %d\\n",\s*input\);',f'last_output={mapping["error"]};',source)
    reset=''.join(f'{name}={value};' for name,value in globals_)
    return 'static int last_output;\n'+source+f'\nvoid __VERIFIER_error(int n){{(void)n;last_output={mapping["error"]};}}\nvoid reset_bench(void){{{reset}}}\nint step_bench(int inp){{last_output=-999;calculate_output(inp);return last_output;}}\n'

def compile_lib(folder,tag,code):
    path=folder/(tag+'.c');path.write_text(code)
    obj=folder/(tag+'.so')
    proc=subprocess.run(['gcc','-std=c99','-O0','-fwrapv','-shared','-fPIC',str(path),'-o',str(obj)],capture_output=True,text=True)
    if proc.returncode:return None,proc.stderr
    lib=ctypes.CDLL(str(obj))
    lib.reset_bench.argtypes=[]
    lib.reset_bench.restype=None
    lib.step_bench.argtypes=[ctypes.c_int]
    lib.step_bench.restype=ctypes.c_int
    return lib,None

def evaluate(lib,cases,mapping,stop_first=True):
    failures=[]
    for index,(sequence,expected) in enumerate(cases):
        lib.reset_bench()
        for k,(inp,out) in enumerate(zip(sequence,expected)):
            got=lib.step_bench(mapping[inp]);wanted=mapping.get(out)
            if got!=wanted:
                failures.append({'test_index':index,'step':k,'inputs':sequence,'expected_symbols':expected,'expected_code':wanted,'actual_code':got})
                break
        if failures and stop_first:break
    return failures

def mutants(source,mapping,seed):
    body=source[:source.index('int main()')]
    start=body.index('void calculate_outputm1(int input)')
    families={}
    outputs=sorted(set(mapping.values()))
    groups=[('output_constant',r'printf\("%d\\n",\s*(\d+)\)',lambda m: m.group(0).replace(m.group(1),str(next(x for x in outputs if x!=int(m.group(1)))),1)),
            ('input_guard',r'input\s*==\s*(\d+)',lambda m:'input == '+str(int(m.group(1))+1)),
            ('delete_state_update',r'\ba\d+\s*=\s*[^;\n]+;',lambda m:';'),
            ('state_constant',r'\ba\d+\s*=\s*(-?\d+)\s*;',lambda m: re.sub(r'=\s*-?\d+', '= '+str(int(m.group(1))+1), m.group(0))),
            ('relational_boundary',r'(?<![<>=!])<(?![<=])',lambda m:'<='),
            ('arithmetic_sign',r'\+\s*\d+',lambda m:m.group(0).replace('+','-',1))]
    rng=random.Random(seed);allmut=[]
    for name,pattern,change in groups:
        matches=[m for m in re.finditer(pattern,body) if m.start()>=start]
        rng.shuffle(matches);families[name]=len(matches)
        for j,m in enumerate(matches[:5]):
            allmut.append({'id':name+f'_{j}','family':name,'start':m.start(),'end':m.end(),'original':m.group(0),'replacement':change(m)})
    return allmut,families

def main():
    prepare();report=[];beg=time.perf_counter()
    for number,model in enumerate(MODELS):
        source,mapping,initial,edges,alphabet=load(model)
        paths,targets,cases=cases_for(initial,edges,alphabet)
        folder=ROOT/model/'run';folder.mkdir(exist_ok=True)
        lib,error=compile_lib(folder,'reference',instrument(source,mapping))
        if lib is None:
            raise RuntimeError('Reference compilation failed for '+model+': '+str(error))
        failures=evaluate(lib,cases,mapping,False)
        result={'benchmark':model,'dot_states':len({a for a,_ in edges}),
                'dot_transitions':len(edges),'common_input_symbols':len(alphabet),
                'reachable_nonerror_states_common_interface':len(paths),'transition_targets':len(targets),
                # Suite length; not total executions across reference and mutants.
                'tests':len(cases),'input_steps':sum(len(s) for s,_ in cases),
                'input_steps_definition':'Sum of generated test lengths; equals reference input executions only when every test completes',
                'reference_failed_tests':len(failures),'reference_first_failure':failures[:1],
                'mutants':[],'scope':'Common mapped input interface; stop at first error; transition targets + one input suffix; original RERS C instrumented for reset/output capture'}
        (ROOT/model/'tests.json').write_text(json.dumps(cases))
        if failures:
            result['mutation_status']='blocked: model/C alignment failed'
        else:
            ms,counts=mutants(source,mapping,20261002+number);result['candidate_sites_by_family']=counts
            for mutant in ms:
                mutation=(mutant['start'],mutant['end'],mutant['replacement'])
                ml,error=compile_lib(folder,mutant['id'],instrument(source,mapping,mutation))
                if not ml:mutant['status']='compile_failed';mutant['diagnostic']=error
                else:
                    witness=evaluate(ml,cases,mapping);mutant['status']='killed' if witness else 'survived';mutant['witness']=witness[:1]
                result['mutants'].append(mutant)
            result['mutant_counts']=dict(Counter(m['status'] for m in result['mutants']))
            result['mutation_status']='completed'
        report.append(result)
        (ROOT/'results.json').write_text(json.dumps(report,indent=2))
        print(json.dumps({k:v for k,v in result.items() if k not in ('mutants','candidate_sites_by_family')},indent=2),flush=True)
    (ROOT/'timing.json').write_text(json.dumps({'elapsed_seconds':time.perf_counter()-beg}))

if __name__=='__main__':main()
