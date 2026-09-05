"""Reproducible behavior checks for command-line coding agents."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import difflib
import html
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from . import __version__
from ._runtime import child_env, command, dump, load, relative, run, sha, snapshot

KINDS = {'exists', 'absent', 'contains', 'unchanged', 'changed'}


def cases(directory):
    result, ids = [], set()
    for path in sorted(Path(directory).glob('*/case.json')):
        spec = load(path)
        ident = spec.get('id', path.parent.name)
        if not isinstance(ident, str) or not ident or ident in ids:
            raise ValueError(f'Duplicate or invalid case id: {ident!r}')
        ids.add(ident)
        if not isinstance(spec.get('prompt'), str) or not spec['prompt'].strip():
            raise ValueError(f'{ident}: prompt must be non-empty text.')
        checks = spec.get('checks')
        if not isinstance(checks, list) or not checks:
            raise ValueError(f'{ident}: at least one check is required.')
        fixture = path.parent / 'fixture'
        if not fixture.is_dir() or fixture.is_symlink():
            raise ValueError(f'{ident}: fixture must be an ordinary directory.')
        before = snapshot(fixture)
        for check in checks:
            if not isinstance(check, dict) or check.get('type') not in KINDS:
                raise ValueError(f'{ident}: unsupported check.')
            name = check.get('path')
            if not isinstance(name, str) or not name or Path(name).as_posix() != name:
                raise ValueError(f'{ident}: use a canonical relative file path.')
            relative(fixture, name)
            if check['type'] == 'contains' and not isinstance(check.get('text'), str):
                raise ValueError(f'{ident}: contains checks need text.')
            if check['type'] in {'changed', 'unchanged'} and name not in before:
                raise ValueError(f'{ident}: {name} must exist for {check["type"]}.')
        fingerprint = sha(json.dumps({'spec': spec, 'fixture': before}, sort_keys=True).encode())
        result.append((ident, spec, fixture, fingerprint))
    if not result:
        raise ValueError('No cases found. Expected CASES/<name>/case.json and fixture/.')
    return result


def evaluate(checks, work, before, after):
    evidence = []
    for check in checks:
        kind, name = check['type'], check['path']
        path = relative(work, name)
        if kind == 'exists': passed = name in after
        elif kind == 'absent': passed = not path.exists()
        elif kind == 'unchanged': passed = before.get(name) == after.get(name)
        elif kind == 'changed': passed = name in after and before.get(name) != after[name]
        else: passed = name in after and check['text'] in path.read_text(encoding='utf-8', errors='replace')
        evidence.append({**check, 'passed': passed})
    return evidence


def run_suite(directory, argv, *, label, version='unspecified', model='unspecified', repeat=1, timeout=120, pass_env=()):
    command(argv)
    if not 1 <= repeat <= 100 or not 0 < timeout <= 3600:
        raise ValueError('Repeat must be 1..100; timeout must be 0 < seconds <= 3600.')
    suite, rows = cases(directory), []
    for ident, spec, fixture, fingerprint in suite:
        for trial in range(1, repeat + 1):
            with tempfile.TemporaryDirectory(prefix='agent-canary-') as temporary:
                base = Path(temporary); work, home = base/'workspace', base/'home'
                shutil.copytree(fixture, work); before = snapshot(work)
                before_text = {name:(work/name).read_text(encoding='utf-8',errors='replace') for name in before}
                prompt_file=base/'prompt.txt'; prompt_file.write_text(spec['prompt'],encoding='utf-8')
                extra={key:os.environ[key] for key in pass_env if key in os.environ}
                extra.update(CANARY_WORKSPACE=str(work),CANARY_PROMPT_FILE=str(prompt_file))
                replacements={'{workspace}':str(work),'{prompt_file}':str(prompt_file),'{prompt}':spec['prompt']}
                resolved=[replacements.get(arg,arg) for arg in argv]
                result=run(resolved,work,timeout=timeout,env=child_env(home,extra),stdin=spec['prompt'])
                evidence,changes,error=[],[],None
                try:
                    after=snapshot(work); evidence=evaluate(spec['checks'],work,before,after)
                    for name in sorted(set(before)|set(after)):
                        if before.get(name)==after.get(name): continue
                        text=(work/name).read_text(encoding='utf-8',errors='replace') if name in after else ''
                        patch=''.join(difflib.unified_diff(before_text.get(name,'').splitlines(True),text.splitlines(True),fromfile='before/'+name,tofile='after/'+name))
                        changes.append({'path':name,'before':before.get(name),'after':after.get(name),'diff':patch[:50000],'diff_truncated':len(patch)>50000})
                except (OSError,ValueError) as exc: error=str(exc)
                passed=(result['status']=='completed' and result['exit_code']==0 and not error and all(c['passed'] for c in evidence))
                rows.append({'case':ident,'fingerprint':fingerprint,'trial':trial,'passed':passed,'checks':evidence,'changes':changes,'evidence_error':error,**result})
    return {'schema':1,'tool':'agent-canary','version':__version__,'created_at':datetime.now(timezone.utc).isoformat(),'agent':label,'agent_version':version,'model':model,'repeat':repeat,'command':argv,'environment_names':list(pass_env),'results':rows,'passed':sum(r['passed'] for r in rows),'total':len(rows)}


def compare(old,new):
    for report in (old,new):
        if report.get('schema')!=1 or report.get('tool')!='agent-canary' or not report.get('results'): raise ValueError('Expected a non-empty Agent Canary schema-1 report.')
    if old['agent']!=new['agent'] or old['model']!=new['model']: raise ValueError('Agent label and model must match; agent version may differ.')
    def group(report):
        buckets={}
        for row in report['results']: buckets.setdefault(row['case'],[]).append(row)
        return buckets
    before,after=group(old),group(new); results=[]
    for ident in sorted(set(before)|set(after)):
        left,right=before.get(ident,[]),after.get(ident,[])
        comparable=(left and right and len(left)==len(right) and len({r['fingerprint'] for r in left})==1 and {r['fingerprint'] for r in left}=={r['fingerprint'] for r in right})
        a,b=sum(r['passed'] for r in left),sum(r['passed'] for r in right)
        status=('regression' if b<a else 'improvement' if b>a else 'unchanged') if comparable else 'not-comparable'
        results.append({'case':ident,'status':status,'before':a,'after':b,'trials_before':len(left),'trials_after':len(right)})
    return results


def render_html(report,path):
    esc=html.escape
    rows=''.join('<tr><td>'+esc(r['case'])+'</td><td>'+str(r['trial'])+'</td><td>'+('PASS' if r['passed'] else 'FAIL')+'</td><td><pre>'+esc(json.dumps(r['checks'],indent=2))+'</pre></td></tr>' for r in report['results'])
    text='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Agent Canary evidence report</title><style>body{font:16px system-ui;max-width:1100px;margin:3rem auto;padding:1rem;background:#101521;color:#e3eaf7}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:1rem;border-bottom:1px solid #38445a}pre{white-space:pre-wrap}h1{color:#ffcc66}</style>'
    text+=f'<h1>Agent Canary</h1><p>{esc(report["agent"])} / {esc(report["agent_version"])} / {esc(report["model"])}</p><p>{report["passed"]}/{report["total"]} observed trials passed. Not a general safety or intelligence score.</p><table><tr><th>Case</th><th>Trial</th><th>Result</th><th>Checks</th></tr>'+rows+'</table></html>'
    Path(path).parent.mkdir(parents=True,exist_ok=True); Path(path).write_text(text,encoding='utf-8')


def main(argv=None):
    parser=argparse.ArgumentParser(description='Executable compatibility evidence for coding agents.'); parser.add_argument('--version',action='version',version=__version__); sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('run'); p.add_argument('cases',type=Path); p.add_argument('--trust',action='store_true',required=True,help='Authorize host execution. NOT a sandbox.'); p.add_argument('--label',required=True); p.add_argument('--agent-version',default='unspecified'); p.add_argument('--model',default='unspecified'); p.add_argument('--repeat',type=int,default=1); p.add_argument('--timeout',type=float,default=120); p.add_argument('--pass-env',action='append',default=[],metavar='NAME'); p.add_argument('--json',type=Path,required=True,dest='report'); p.add_argument('--html',type=Path); p.add_argument('--command',nargs=argparse.REMAINDER,required=True)
    p=sub.add_parser('compare'); p.add_argument('before',type=Path); p.add_argument('after',type=Path); p.add_argument('--json',type=Path,dest='report'); args=parser.parse_args(argv)
    try:
        if args.action=='run':
            report=run_suite(args.cases,args.command,label=args.label,version=args.agent_version,model=args.model,repeat=args.repeat,timeout=args.timeout,pass_env=args.pass_env); dump(args.report,report)
            if args.html: render_html(report,args.html)
            for row in report['results']: print(f'{"PASS" if row["passed"] else "FAIL"} {row["case"]} trial {row["trial"]}')
            print(f'{report["passed"]}/{report["total"]} trials passed. Evidence: {args.report}'); return 0 if report['passed']==report['total'] else 1
        changes=compare(load(args.before),load(args.after))
        if args.report: dump(args.report,changes)
        for row in changes: print(f'{row["status"].upper()} {row["case"]}: {row["before"]} -> {row["after"]} passing trials')
        return 1 if any(r['status']=='regression' for r in changes) else 2 if any(r['status']=='not-comparable' for r in changes) else 0
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
        print(f'agent-canary: {exc}',file=sys.stderr); return 2


def entrypoint(): raise SystemExit(main())
