"""Regenera tablas y figuras embebidas desde evidencia registrada, sin ejecutar solvers.

Ejecutar desde cualquier carpeta: python technical_report/preparar_datos.py.
El manuscrito sigue siendo un documento LaTeX autónomo para el editor integrado.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
TEX = OUT / 'yoguicuentas_paper_20261030.tex'
INPUTS = [
    'verification/2026-10-29/numerical/report.json',
    'verification/2026-10-29/m1-review/audit.json',
    'verification/2026-10-29/m1/final-02/mediciones.csv',
    'verification/2026-10-29/m1/benchmark-final/timings.csv',
]

def read_csv(name):
    with (ROOT / name).open() as f:
        return list(csv.DictReader(f))

def coords(points):
    return ' '.join(f'({x:.12g},{y:.12g})' for x, y in points)

def table(headers, rows, caption, label, alignment):
    return '\n'.join([
        r'\begin{table}' + ('[H]' if label == 'tab:full-cost' else '[tbp]') + r'\centering\small',
        '\\caption{' + caption + '}\\label{' + label + '}',
        '\\begin{tabular}{@{}' + alignment + '@{}}\\toprule',
        ' & '.join(headers) + r'\\\midrule',
        *(' & '.join(row) + r'\\' for row in rows),
        r'\bottomrule\end{tabular}\end{table}',
    ])

def main():
    linux = json.loads((ROOT / INPUTS[0]).read_text())
    audit = json.loads((ROOT / INPUTS[1]).read_text())
    assert linux['passed'] and audit['passed']
    assert len(linux['checks']) == 217
    measurements = read_csv(INPUTS[2])
    timings = read_csv(INPUTS[3])
    assert len(measurements) == 60 and len(timings) == 120
    order_rows = []
    temporal = {}
    for backend, label in [('numpy', 'NumPy'), ('opencl', 'OpenCL'),
                           ('Swift-float32', 'Swift'), ('Metal-float32', 'Metal')]:
        result = {'backend': label}
        for family in ['temporal', 'spatial']:
            for method, slug in [('Euler', 'explicit'), ('CN', 'crankNicolson')]:
                if backend in ('numpy', 'opencl'):
                    values = [e for e in linux['experiments']
                              if e['backend'] == backend and e['case'].startswith(f'{family}/{slug}/')]
                    points = [(e['dt'] if family == 'temporal' else e['dx'], e['error_linf_K']) for e in values]
                else:
                    values = [e for e in measurements if e['backend'] == backend and e['case'] == f'{family}-{method}']
                    points = [(float(e['dt'] if family == 'temporal' else e['dx']), float(e['error'])) for e in values]
                points.sort(reverse=True)
                assert len(points) == 3 and all(y > 0 for _, y in points)
                orders = [math.log2(points[i][1] / points[i+1][1]) for i in range(2)]
                result[f'{family}-{method}'] = orders
                if family == 'temporal':
                    temporal[(label, method)] = points
        order_rows.append(result)
    parts = {}
    rows = [[r['backend']] + [' / '.join(f'{p:.4f}' for p in r[key])
            for key in ['temporal-Euler', 'temporal-CN', 'spatial-Euler', 'spatial-CN']]
            for r in order_rows]
    parts['ORDER_TABLE'] = table(['Implementación', 'Euler temporal', 'CN temporal', 'Euler espacial', 'CN espacial'], rows,
        'Órdenes observados entre los tres niveles de refinamiento. Cada celda muestra los dos órdenes sucesivos.', 'tab:orders', 'lrrrr')
    lines = [r'\begin{figure}[tbp]\centering']
    colors = ['blue!75!black', 'red!75!black', 'teal!75!black', 'orange!90!black']
    markers = ['*', 'square*', 'triangle*', 'diamond*']
    for method in ['Euler', 'CN']:
        lines += [r'\begin{minipage}{.49\linewidth}\centering', r'\begin{tikzpicture}',
            '\\begin{loglogaxis}[width=.94\\linewidth,height=5.9cm,title={' + method +
            r'},xlabel={Paso $\Delta t$ [s]},ylabel={Error $L_\infty$ [K]},grid=major,'
            r'legend style={font=\scriptsize,at={(0.03,0.03)},anchor=south west},'
            r'tick label style={font=\scriptsize},label style={font=\small},scaled ticks=false]']
        for label, color, marker in zip(['NumPy', 'OpenCL', 'Swift', 'Metal'], colors, markers):
            lines += [f'\\addplot+[color={color},mark={marker},solid] coordinates {{{coords(temporal[(label, method)])}}};',
                      '\\addlegendentry{' + label + '}']
        lines += [r'\end{loglogaxis}\end{tikzpicture}\end{minipage}']
    lines += [r'\caption{Refinamiento temporal frente al modo semidiscreto, $9\times7$ nodos, $t=0.4$ s. Las curvas CPU/GPU casi se superponen; no representan ocho réplicas independientes. Los puntos son errores registrados, sin ajuste.}\label{fig:temporal}',r'\end{figure}']
    parts['TEMPORAL_FIGURE'] = '\n'.join(lines)
    robin = audit['robin_staircase']
    parts['ROBIN_TABLE'] = table(['Grilla', '$G_h$', '$G_{ideal}$', 'Exceso [\\%]'],
        [[f"${r['nx']}^2$", f"{r['conductance_W_K']:.6f}", f"{r['ideal_W_K']:.6f}", f"{r['relative_error_percent']:.3f}"] for r in robin],
        'Conductancia Robin circular por unidad de espesor, en W/(m K). El campo de origen denomina W/K a la conductancia para espesor unitario.', 'tab:robin', 'lrrr')
    parts['ROBIN_FIGURE'] = '\n'.join([
        r'\begin{figure}[tbp]\centering\begin{tikzpicture}',
        r'\begin{axis}[width=.82\linewidth,height=5.6cm,xmode=log,log basis x=2,xlabel={Nodos por dirección $n$},ylabel={Exceso de conductancia [\%]},grid=major,xtick={41,81,161},xticklabels={41,81,161},legend style={font=\small,at={(0.97,0.97)},anchor=north east}]',
        '\\addplot+[blue!75!black,mark=*,solid] coordinates {' + coords([(r['nx'], r['relative_error_percent']) for r in robin]) + '};',
        r'\addlegendentry{Ensayo registrado}',
        r'\addplot[red!75!black,dashed,domain=41:161] {27.3239544735};',
        r'\addlegendentry{Límite geométrico $100(4/\pi-1)$}',
        r'\end{axis}\end{tikzpicture}',
        r'\caption{Refinar reduce parte del error de frontera pero no el exceso límite de perímetro escalonado. La línea horizontal es la predicción geométrica, no un ajuste a los tres puntos.}\label{fig:robin}\end{figure}',
    ])
    summary = audit['benchmark_summary']
    import statistics
    for row in summary:
        for backend, key in [('Swift', 'median_swift_s'), ('Metal', 'median_metal_s')]:
            observed = [float(t['seconds']) for t in timings if int(t['nx']) == row['nx'] and t['method'] == row['method'] and t['backend'] == backend]
            assert len(observed) == 3 and math.isclose(statistics.median(observed), row[key], rel_tol=1e-12)
    parts['TIMING_TABLE'] = table(['Método', 'Swift [s]', 'Metal [s]', 'Swift/Metal'],
        [[r['method'], f"{r['median_swift_s']:.6f}", f"{r['median_metal_s']:.6f}", f"{r['swift_time_over_metal_time']:.2f}"] for r in summary if r['nx'] == 257],
        'Tiempo mediano de 64 pasos/barridos en $257^2$ nodos, tres repeticiones. El cociente compara procesadores dentro de cada método, no eficiencia entre métodos.', 'tab:timing', 'lrrr')
    parts['FULL_TIMING_TABLE'] = table(['$n_x=n_y$', 'Método', 'Swift [s]', 'Metal [s]', 'Swift/Metal'],
        [[str(r['nx']), r['method'], f"{r['median_swift_s']:.7f}", f"{r['median_metal_s']:.7f}", f"{r['swift_time_over_metal_time']:.3f}"] for r in summary],
        'Medianas de los 120 tiempos M1, agrupados en 40 combinaciones tamaño/método/procesador. Los escenarios y las repeticiones individuales se conservan con la evidencia.', 'tab:full-cost', 'rlrrr')
    lines = [r'\begin{figure}[tbp]\centering\begin{tikzpicture}',
             r'\begin{loglogaxis}[width=.88\linewidth,height=6.5cm,xlabel={Nodos totales $N=n^2$},ylabel={Tiempo Swift / tiempo Metal},grid=major,legend style={font=\small,at={(0.03,0.97)},anchor=north west},ymin=0.01,ymax=30]']
    for method, color, marker in zip(['Euler', 'CN', 'Jacobi', 'GS'], colors, markers):
        points = [(r['nx'] ** 2, r['swift_time_over_metal_time']) for r in summary if r['method'] == method]
        lines += [f'\\addplot+[color={color},mark={marker},solid] coordinates {{{coords(points)}}};', '\\addlegendentry{' + method + '}']
    lines += [r'\addplot[black,dashed,domain=289:66049] {1};\addlegendentry{Igual tiempo}',r'\end{loglogaxis}\end{tikzpicture}',
              r'\caption{Cocientes de medianas en M1 para 64 pasos/barridos. Valores mayores que uno favorecen Metal; menores que uno favorecen Swift. Se incluyen transferencias de campo Metal; no se mide tiempo hasta igual error ni se compara A2000 con M1.}\label{fig:cost}\end{figure}']
    parts['COST_FIGURE'] = '\n'.join(lines)
    text = TEX.read_text()
    for key, value in parts.items():
        begin, end = f'% BEGIN AUTO {key}', f'% END AUTO {key}'
        block = begin + '\n' + value + '\n' + end
        if f'@@{key}@@' in text:
            text = text.replace(f'@@{key}@@', block)
        else:
            pattern = re.escape(begin) + r'.*?' + re.escape(end)
            text, count = re.subn(pattern, lambda _: block, text, flags=re.S)
            assert count == 1, key
    assert not re.search(r'@@[A-Z_]+@@', text)
    TEX.write_text(text)
    data = {'description': 'Derived manuscript numbers from recorded evidence; no solver execution',
            'inputs_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in INPUTS},
            'orders': order_rows, 'timing_medians': summary, 'robin_staircase': robin,
            'recorded_xctest': audit['recorded_xctest'], 'linux_checks': len(linux['checks']),
            'temporal_errors': {f'{backend}-{method}': points for (backend, method), points in temporal.items()}}
    (OUT / 'datos_manuscrito.json').write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    print('Tablas y figuras regeneradas; 217 controles, 60 mediciones y 120 tiempos identificados por hash.')

if __name__ == '__main__':
    main()
