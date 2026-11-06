"""Optional figures: python verification/graficar.py path/to/report.json.

Requires matplotlib in the environment used for plotting, not in the application.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    args=parser.parse_args()
    report=json.loads(args.report.read_text());rows=report['experiments']
    fig,axes=plt.subplots(2,2,figsize=(12,9),layout='constrained')
    colors={'explicit':'#1769aa','crankNicolson':'#b64b15','jacobi':'#6e4aa5','gaussSeidel':'#16806a'}
    labels={'explicit':'Euler','crankNicolson':'CN','jacobi':'Jacobi','gaussSeidel':'Gauss–Seidel R/N'}
    names={'numpy':'CPU float64','opencl':'GPU float32'}
    for backend in ('numpy','opencl'):
        style='-' if backend=='numpy' else '--'
        marker='o' if backend=='numpy' else 's'
        for method in ('explicit','crankNicolson'):
            for prefix,ax,key in (('spatial/',axes[0,0],'dx'),('temporal/',axes[0,1],'dt')):
                data=sorted((r for r in rows if r['backend']==backend and r['method']==method and r['case'].startswith(prefix)),key=lambda r:r[key])
                if data:
                    ax.loglog([r[key] for r in data],[r['error_linf_K'] for r in data],
                              linestyle=style,marker=marker,color=colors[method],label=f'{labels[method]} · {names[backend]}')
        data=sorted((r for r in rows if r['backend']==backend and r['case'].startswith('curved/')),key=lambda r:r['dx'])
        if data:
            axes[1,0].loglog([r['dx'] for r in data],[r['error_linf_K'] for r in data],linestyle=style,marker=marker,
                            color='#6e4aa5',label=names[backend])
        for method in colors:
            data=sorted((r for r in rows if r['backend']==backend and r['method']==method and r['case']=='cost/fixed-64-sweeps'),key=lambda r:r['nodes'])
            if data:
                axes[1,1].loglog([r['nodes'] for r in data],[r['wall_s'] for r in data],linestyle=style,marker=marker,
                                color=colors[method],label=f'{labels[method]} · {names[backend]}')
    titles=('Refinamiento espacial · rectángulo suave','Refinamiento temporal · modo semidiscreto',
            'Círculo rasterizado · error geométrico incluido','Costo observado · 64 pasos o barridos completos')
    for ax,title in zip(axes.flat,titles):
        ax.set_title(title,fontsize=11);ax.grid(True,which='both',alpha=.22)
        ax.legend(fontsize=8,loc='best',ncol=2 if ax is axes[1,1] else 1)
    axes[0,0].set_xlabel('dx [m]');axes[0,1].set_xlabel('dt [s]');axes[1,0].set_xlabel('dx = dy [m]')
    axes[1,1].set_xlabel('Nodos totales');axes[1,1].set_ylabel('Tiempo de pared [s]')
    for ax in (axes[0,0],axes[0,1],axes[1,0]):ax.set_ylabel('Error máximo de temperatura [K]')
    device=report['metadata'].get('opencl_device',{}).get('name','sin GPU')
    fig.suptitle(f'YoguiCuentas · grilla cartesiana estructurada · {device}\n'
                 'Mediciones del equipo con carga no aislada; no comparan igual tiempo físico entre métodos',fontsize=12)
    for suffix in ('png','svg'):
        fig.savefig(args.report.parent/f'convergencia-costo.{suffix}',dpi=160)
    plt.close(fig)


if __name__=='__main__':main()
