"""Read-only audit of the received M1 campaign; never executes supplied code.

python verification/revisar_m1.py metal_test_00 --output verification/2026-10-29/m1-review
"""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import struct


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def rows(path):
    with path.open() as f:return list(csv.DictReader(f))
def float32(value):return struct.unpack('<f',struct.pack('<f',float(value)))[0]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('received',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.received;project=root/'yoguicuentas_metal'
    run=project/'verification/m1-20261029';final=run/'final-02'
    report={'scope':'Offline integrity and arithmetic audit of recorded M1 results; no Mac code executed here',
            'received_directory':str(root),'manifests':{}}
    for name,base in [('fuentes_finales.sha256',project),('final-02/fuentes.sha256',project),
                      ('benchmark-final/fuentes.sha256',project),('entrega.sha256',run)]:
        matched=0
        for line in (run/name).read_text().splitlines():
            digest,relative=line.split('  ',1)
            path=Path(relative)
            assert not path.is_absolute() and '..' not in path.parts,relative
            p=base/path
            if not p.is_file() and relative.startswith('YoguiCuentas Metal.app/'):p=root/path
            assert p.is_file() and sha(p)==digest,(name,relative)
            matched+=1
        report['manifests'][name]={'entries':matched,'matched':matched}
    binary=root/'YoguiCuentas Metal.app/Contents/MacOS/yoguicuentas_metal'
    report['binary_sha256']=sha(binary)
    assert report['binary_sha256']==(run/'binario.sha256').read_text().split()[0]
    log=(final/'swift-test.log').read_text()
    assert 'Executed 103 tests, with 0 failures' in log
    assert len(re.findall(r"Test Case .* passed \(",log))==103
    assert not re.search(r'Test Case .* (failed|skipped)',log)
    report['recorded_xctest']={'passed':103,'failed':0,'skipped':0,'exit_status':int((final/'exit-status.txt').read_text())}
    assert report['recorded_xctest']['exit_status']==0
    records=[json.loads(line) for line in (final/'campaign.jsonl').read_text().splitlines()]
    assert len(records)==158
    criteria=[r for r in records if r['case']=='criterion'];assert len(criteria)==144
    unique={(r['method'],r['backend'],r['sampling'],r['criterion']) for r in criteria};assert len(unique)==144
    report['campaign_records']=dict(collections.Counter(r['case'] for r in records))
    report['criterion_stop_reasons']=dict(collections.Counter(r['reason'] for r in criteria))
    verified=0
    for path in sorted((final/'artifacts').glob('*.metadata.json')):
        m=json.loads(path.read_text());stem=path.name.removesuffix('.metadata.json')
        field=rows(path.with_name(stem+'.csv'));history=rows(path.with_name(stem+'.convergence.csv'))
        scenario=json.loads(path.with_name(stem+'.scenario.json').read_text());g=scenario['canvas']
        assert len(field)==g['nx']*g['ny'] and len(history)==m['historyCount']
        assert m['effectiveBackend']==m['requestedBackend']
        assert int(history[-1]['step'])==m['steps'] and history[-1]['stop_reason']==m['stopReason']
        if m['countUnit']=='iterations':assert m.get('physicalTimeSeconds') is None and m.get('dtSeconds') is None
        if m['stopReason']=='converged':assert m['physicalConfirmations']>=g['time']['confirmations']
        if m['stopReason']=='max_steps':assert m['steps']==g['time']['maxSteps']
        for v in field:
            assert math.isfinite(float(v['temperatura_C']))
            assert abs(float(v['x_m'])-int(v['i'])*g['Lx']/(g['nx']-1))<1e-12
            assert abs(float(v['y_m'])-int(v['j'])*g['Ly']/(g['ny']-1))<1e-12
        verified+=1
    assert verified==144;report['consistent_export_sets']=verified
    numeric=rows(final/'mediciones.csv');assert len(numeric)==60
    report['smooth_convergence_orders']={}
    for backend in ('Swift-float32','Metal-float32'):
        orders={}
        for case,key in [('temporal-Euler','dt'),('temporal-CN','dt'),('spatial-Euler','dx'),('spatial-CN','dx')]:
            data=sorted((r for r in numeric if r['case']==case and r['backend']==backend),key=lambda r:float(r[key]),reverse=True)
            assert len(data)==3
            orders[case]=[math.log2(float(a['error'])/float(b['error'])) for a,b in zip(data,data[1:])]
        report['smooth_convergence_orders'][backend]=orders
    # Recompute the comparison of analytic errors against the original Linux data.
    linux=rows(Path(__file__).resolve().parents[1]/'verification/2026-10-29/numerical/experiments.csv')
    comparisons=rows(run/'comparison_linux_m1.csv');assert len(comparisons)==48
    for r in comparisons:
        family,method=r['case'].split('-');method={'Euler':'explicit','CN':'crankNicolson'}[method]
        match=[x for x in linux if x['backend']==r['linux_backend'] and x['case'].startswith(f'{family}/{method}/')
               and x['nodes']==r['nodes'] and math.isclose(float(x['dt']),float(r['dt']),rel_tol=1e-10)]
        assert len(match)==1,r
        assert math.isclose(float(match[0]['error_linf_K']),float(r['linux_error_K']),rel_tol=1e-10,abs_tol=1e-14)
        assert math.isclose(abs(float(r['m1_error_K'])-float(r['linux_error_K'])),float(r['absolute_difference_of_errors_K']),rel_tol=1e-9,abs_tol=1e-14)
    report['analytic_error_comparisons_verified']=len(comparisons)
    report['note_analytic_comparison']='Compares errors against analytical references, not M1-vs-A2000 fields or timings'
    times=rows(run/'benchmark-final/timings.csv');assert len(times)==120
    assert all(math.isfinite(float(r['seconds'])) and float(r['seconds'])>0 and int(r['steps_or_sweeps'])==64 for r in times)
    groups=collections.defaultdict(list)
    for r in times:groups[(int(r['nx']),r['method'],r['backend'])].append(float(r['seconds']))
    assert len(groups)==40 and all(len(v)==3 for v in groups.values())
    report['benchmark_summary']=[]
    for n in (17,33,65,129,257):
        for method in ('Euler','CN','Jacobi','GS'):
            cpu=statistics.median(groups[n,method,'Swift']);gpu=statistics.median(groups[n,method,'Metal'])
            report['benchmark_summary'].append({'nx':n,'method':method,'median_swift_s':cpu,'median_metal_s':gpu,'swift_time_over_metal_time':cpu/gpu})
    paired=[]
    for method in ('Euler','CN','Jacobi','GS'):
        for n in (17,65):
            cpu=rows(run/f'benchmark-final/{method}-Swift-{n}.csv');gpu=rows(run/f'benchmark-final/{method}-Metal-{n}.csv')
            assert len(cpu)==len(gpu)==n*n
            for a,b in zip(cpu,gpu):assert all(a[k]==b[k] for k in ('i','j','x_m','y_m','active'))
            error=max(abs(float32(a['temperature_C'])-float32(b['temperature_C'])) for a,b in zip(cpu,gpu))
            paired.append({'method':method,'nx':n,'linf_K':error})
    report['saved_field_pairs']=paired
    report['max_recorded_float32_cpu_gpu_K']=max(float(r['cpu_gpu_linf_K']) for r in times)
    report['max_recomputed_saved_field_pair_K']=max(r['linf_K'] for r in paired)
    assert report['max_recomputed_saved_field_pair_K']<=report['max_recorded_float32_cpu_gpu_K']+1e-12
    report['boundary_balance_max_absolute_error_J_m']=max(r['error_J_m'] for r in records if r['case']=='transient-boundary-balance')
    report['high_frequency']=[r for r in records if r['case']=='high-frequency']
    report['circle_refinement']=[r for r in records if r['case']=='circle']
    robin=[]
    for n,g,ideal,error in re.findall(r'Robin staircase n=(\d+): G=([\d.eE+-]+) W/K, ideal=([\d.eE+-]+), relative error=([\d.eE+-]+)%',log):
        robin.append({'nx':int(n),'conductance_W_K':float(g),'ideal_W_K':float(ideal),'relative_error_percent':float(error)})
    assert len(robin)==3;report['robin_staircase']=robin
    report['square_staircase_perimeter_limit_excess_percent']=(4/math.pi-1)*100
    report['passed']=True
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'integrity':'all matched','tests':report['recorded_xctest'],'export_sets':verified,
                      'campaign_records':report['campaign_records'],'timings':len(times),
                      'max_recomputed_field_difference_K':report['max_recomputed_saved_field_pair_K']},indent=2))


if __name__=='__main__':main()
