"""Editor de rectángulos, con presets de material o propiedades propias."""
import tkinter as tk
from tkinter import ttk, messagebox
from ..model.regions import Region, MEANS
from ..model.materials import MATERIALS, CUSTOM


class RegionEditor(ttk.Frame):
    def __init__(self,parent,regions,mean,dimensions):
        super().__init__(parent,padding=10)
        self.regions=list(regions)
        self.dimensions=dimensions
        self.mean=tk.StringVar(value=mean)
        bar=ttk.Frame(self);bar.pack(fill='x')
        ttk.Label(bar,text='Cantidad:').pack(side='left')
        self.count=tk.StringVar(value=str(len(regions)))
        ttk.Spinbox(bar,from_=0,to=256,textvariable=self.count,width=5).pack(side='left',padx=4)
        ttk.Button(bar,text='Crear franjas X',command=self.stripes).pack(side='left',padx=4)
        ttk.Label(bar,text='Interfaz:').pack(side='left',padx=6)
        ttk.Combobox(bar,textvariable=self.mean,values=MEANS,state='readonly',width=15).pack(side='left')
        columns=('material','x','y','k')
        table=ttk.Frame(self);table.pack(fill='both',expand=True,pady=8)
        self.tree=ttk.Treeview(table,columns=columns,show='headings',height=7,selectmode='browse')
        for col,label,width in zip(columns,('Material','X [m]','Y [m]','k [W/(m K)]'),(175,125,125,105)):
            self.tree.heading(col,text=label);self.tree.column(col,width=width)
        scroll=ttk.Scrollbar(table,orient='vertical',command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left',fill='both',expand=True)
        scroll.pack(side='right',fill='y')
        self.tree.bind('<Double-1>',lambda e:self.edit())
        actions=ttk.Frame(self);actions.pack(fill='x')
        ttk.Button(actions,text='Agregar región',command=self.add).pack(side='left',padx=3)
        ttk.Button(actions,text='Editar seleccionada…',command=self.edit).pack(side='left',padx=3)
        ttk.Button(actions,text='Eliminar seleccionada',command=self.remove).pack(side='left',padx=3)
        ttk.Label(self,text='El material de fondo cubre lo no definido. No se permiten solapamientos.\n'
                  'Crear franjas reemplaza la lista. Luego editar límites y material de cada fila.\n'
                  'Rectángulos [mín, máx); se incluye el extremo exterior del dominio.\n'
                  'Armónica: recomendada; aritmética y geométrica: comparación experimental.',
                  justify='left').pack(anchor='w',pady=8)
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i,r in enumerate(self.regions):
            self.tree.insert('', 'end',iid=str(i),values=(r.name,f'{r.xmin:g} – {r.xmax:g}',
                                                        f'{r.ymin:g} – {r.ymax:g}',f'{r.conductivity:g}'))
        self.count.set(str(len(self.regions)))

    def stripes(self):
        try:
            n=int(self.count.get())
            if not 0<=n<=256:
                raise ValueError('Cantidad entre 0 y 256')
            lx,ly=self.dimensions()
            if lx<=0 or ly<=0:
                raise ValueError('Dimensiones positivas')
            k,rho,cp=MATERIALS['Cu — Cobre']
            rows=[Region(i*lx/n,(i+1)*lx/n,0,ly,k,rho,cp,'Cu — Cobre') for i in range(n)]
        except (ValueError,OverflowError) as exc:
            messagebox.showerror('Regiones inválidas',str(exc),parent=self)
            return
        self.regions=rows
        self.refresh()

    def add(self):
        try:
            lx,ly=self.dimensions()
            r=Region(0,lx,0,ly,*MATERIALS['Cu — Cobre'],'Cu — Cobre')
        except (ValueError,OverflowError) as exc:
            messagebox.showerror('Región inválida',str(exc),parent=self);return
        self.edit_region(r,None)

    def edit(self):
        selected=self.tree.selection()
        if selected:
            index=int(selected[0])
            self.edit_region(self.regions[index],index)

    def remove(self):
        selected=self.tree.selection()
        if selected:
            del self.regions[int(selected[0])]
            self.refresh()

    def edit_region(self,region,index):
        dialog=tk.Toplevel(self)
        dialog.title('Material y límites de región')
        dialog.transient(self.winfo_toplevel())
        entries={}
        for row,(name,label,value) in enumerate((('xmin','X mínimo (m)',region.xmin),
                   ('xmax','X máximo (m)',region.xmax),('ymin','Y mínimo (m)',region.ymin),
                   ('ymax','Y máximo (m)',region.ymax))):
            ttk.Label(dialog,text=label).grid(row=row,column=0,padx=8,pady=4)
            var=tk.StringVar(value=str(value));entries[name]=var
            ttk.Entry(dialog,textvariable=var,width=23).grid(row=row,column=1,padx=8,pady=4)
        chosen=next((name for name,values in MATERIALS.items() if values==(
            region.conductivity,region.density,region.specific_heat)),CUSTOM)
        material=tk.StringVar(value=chosen)
        ttk.Label(dialog,text='Material').grid(row=4,column=0,padx=8)
        combo=ttk.Combobox(dialog,textvariable=material,values=[*MATERIALS,CUSTOM],state='readonly')
        combo.grid(row=4,column=1,padx=8,pady=4)
        widgets=[]
        for row,(name,label,value) in enumerate((('conductivity','k (W/(m K))',region.conductivity),
                   ('density','ρ (kg/m³)',region.density),('specific_heat','cp (J/(kg K))',region.specific_heat)),5):
            ttk.Label(dialog,text=label).grid(row=row,column=0,padx=8,pady=4)
            var=tk.StringVar(value=str(value));entries[name]=var
            widget=ttk.Entry(dialog,textvariable=var,width=23);widgets.append(widget)
            widget.grid(row=row,column=1,padx=8,pady=4)
        def change(event=None):
            if material.get() in MATERIALS:
                for key,value in zip(('conductivity','density','specific_heat'),MATERIALS[material.get()]):
                    entries[key].set(str(value))
            for widget in widgets:
                widget.configure(state='normal' if material.get()==CUSTOM else 'readonly')
        combo.bind('<<ComboboxSelected>>',change);change()
        def accept():
            try:
                new=Region(**{key:float(var.get()) for key,var in entries.items()},name=material.get())
            except (ValueError,OverflowError) as exc:
                messagebox.showerror('Región inválida',str(exc),parent=dialog);return
            if index is None:
                self.regions.append(new)
            else:
                self.regions[index]=new
            self.refresh();dialog.destroy()
        ttk.Button(dialog,text='Aceptar región',command=accept).grid(row=8,column=1,pady=10)
        ttk.Button(dialog,text='Cancelar',command=dialog.destroy).grid(row=8,column=0,pady=10)
        return dialog
