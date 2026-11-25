import hashlib,json,pathlib,subprocess,time
r=pathlib.Path('/Users/agrudin/dev/my/ariadna'); out=pathlib.Path('/private/tmp/ariadna-f7-20261125')
def snapshot():
    raw=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=r).decode().split('\0')
    return {'files':{p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in sorted(set(raw)) if p},'git_status':subprocess.check_output(['git','status','--porcelain'],cwd=r).decode(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=r).decode().strip()}
before=snapshot(); (out/'frozen-checkout.json').write_text(json.dumps(before,indent=2)+'\n')
results=[]
for lane,flags in [('portable',['--offline']),('live',['-m','live'])]:
    started=time.monotonic(); command=['/opt/homebrew/bin/conda','run','--no-capture-output','-n','space-nav','python','-m','pytest','-q','-ra',*flags,'--junitxml='+str(out/(lane+'.xml'))]
    with (out/(lane+'.log')).open('xb') as log:
        process=subprocess.run(command,cwd=r,stdout=log,stderr=subprocess.STDOUT,check=False)
    after=snapshot(); unchanged=before==after
    result={'lane':lane,'command':command,'returncode':process.returncode,'elapsed_s':time.monotonic()-started,'checkout_unchanged':unchanged,'file_count':len(before['files'])}
    results.append(result); (out/'regression-status.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    if process.returncode or not unchanged:
        raise SystemExit(2)
(out/'freeze-verification.json').write_text(json.dumps({'status':'passed','files':len(before['files']),'both_lanes':results,'final_snapshot_matches':snapshot()==before},indent=2)+'\n')
