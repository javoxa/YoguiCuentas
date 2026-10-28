#!/usr/bin/env python3
"""Render an entirely self-contained LaTeX report from archived measurements."""
from pathlib import Path
import csv
import json
import math

root = Path(__file__).resolve().parents[1]
data = json.loads((root / 'data/measurements.json').read_text())
template = (root / 'scripts/report_template.tex.in').read_text()

def coordinates(rows):
    return ' '.join(f'({float(x):.10g},{float(y):.10g})' for x, y in rows)

def scientific(value):
    if value == 0:
        return '0'
    exponent = math.floor(math.log10(abs(value)))
    return f'{value / 10**exponent:.4f}\\times10^{{{exponent}}}'

def escape(value):
    return str(value).replace('&', r'\&').replace('%', r'\%').replace('_', r'\_').replace('#', r'\#')

rows = []
for method in ['CN', 'Euler']:
    series = [r for r in data['temporal'] if r['method'] == method]
    previous = None
    for r in series:
        order = '--' if previous is None else f"{math.log2(previous/r['cpu_error']):.3f}"
        rows.append(f"{method} & {r['dt']:.4f} & {r['steps']} & ${scientific(r['cpu_error'])}$ & {order} " + r'\\')
        previous = r['cpu_error']
    if method == 'CN':
        rows.append(r'\addlinespace')

curves = []
styles = ['azul,mark=*', 'verde,mark=square*', 'rojo,mark=triangle*']
for record, style in zip(data['jacobi'], styles):
    points = [[p[0], p[1]/record['curve'][0][1]] for p in record['curve'] if p[1] > 0]
    curves.append(r'\addplot[thick,'+style+r',mark repeat=8] coordinates {'+coordinates(points)+r'};'+
                  r'\addlegendentry{$'+str(record['n'])+r'\times'+str(record['n'])+r'$}')
    with (root / f"data/jacobi_{record['n']}.csv").open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['iterations', 'residual_max_K_per_s', 'residual_weighted_L1_W_at_b_1m'])
        writer.writerows(record['curve'])

cn = [r for r in data['temporal'] if r['method'] == 'CN']
replacements = {
    'GPU': escape(data['gpu']),
    'OS': escape(data['os']),
    'POSITIVITY': coordinates(data['positivity']['history']),
    'TEMPORAL_TABLE': '\n'.join(rows),
    'GAP': scientific(max(r.get('cpu_gpu_max', 0) for r in cn)),
    'CN_ERROR': coordinates([[r['dt'], r['cpu_error']] for r in cn]),
    'FE_ERROR': coordinates([[r['dt'], r['cpu_error']] for r in data['temporal'] if r['method'] == 'Euler']),
    'JACOBI_TABLE': '\n'.join(f"{r['n']} & {(r['n']-2)**2} & {r['iterations']} & ${scientific(r['rate_limit'])}$ " + r'\\' for r in data['jacobi']),
    'JACOBI_CURVES': '\n'.join(curves),
    'ROBIN_TABLE': '\n'.join(f"{r['n']} & {r['dx']:.6f} & {r['conductance']:.6f} & {100*r['relative_error']:.3f} " + r'\\' for r in data['robin']),
    'ROBIN_CURVE': coordinates([[r['n'], r['conductance']] for r in data['robin']]),
}
for key, value in replacements.items():
    template = template.replace('@@'+key+'@@', value)
if '@@' in template:
    raise ValueError('Unresolved report token')
output = root / 'informe_tecnico_yoguicuentas_metal.tex'
output.write_text(template)
for name in ['temporal', 'robin']:
    records = data[name]
    keys = sorted({key for row in records for key in row})
    with (root / f'data/{name}.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows(records)
print(output)
