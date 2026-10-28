"""Editor de fuentes constantes. La plantilla existe sin activarse por defecto."""
import tkinter as tk
from tkinter import ttk,messagebox
from ..model.sources import HeatSource,GEOMETRIES,template_source


class SourceEditor(ttk.Frame):
    def __init__(self,parent,sources,dimensions):
        super().__init__(parent,padding=10)
        self.sources=list(sources);self.dimensions=dimensions
        bar=ttk.Frame(self);bar.pack(fill='x')
        ttk.Label(bar,text='Cantidad:').pack(side='left')
        self.count=tk.StringVar(value=str(len(sources)))
        ttk.Spinbox(bar,from_=0,to=256,textvariable=self.count,width=5).pack(side='left',padx=4)
        ttk.Button(bar,text='Crear fuentes cuadradas',command=self.create).pack(side='left',padx=4)
        table=ttk.Frame(self);table.pack(fill='both',expand=True,pady=8)
        self.tree=ttk.Treeview(table,columns=('geometry','position','size','q'),show='headings',
                               height=7,selectmode='browse')
        for key,label,width in zip(('geometry','position','size','q'),
                                   ('Geometría','Centro (x,y) [m]','Tamaño [m]','Q [W/m³]'),
                                   (120,155,140,120)):
            self.tree.heading(key,text=label);self.tree.column(key,width=width)
        self.tree.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(table,orient='vertical',command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y')
        self.tree.bind('<Double-1>',lambda e:self.edit())
        actions=ttk.Frame(self);actions.pack(fill='x')
        ttk.Button(actions,text='Agregar cuadrada…',command=self.add).pack(side='left',padx=3)
        ttk.Button(actions,text='Editar fuente…',command=self.edit).pack(side='left',padx=3)
        ttk.Button(actions,text='Eliminar fuente',command=self.remove).pack(side='left',padx=3)
        ttk.Label(self,text='Origen (0,0): esquina inferior izquierda. (x,y) es el centro en metros.\n'
                  'Q es constante en el tiempo: positivo calienta, negativo enfría.\n'
                  'Las fuentes superpuestas se suman al fondo uniforme de la primera pestaña.\n'
                  'Lista vacía y Q de fondo=0 ⇒ S(x,y)=0. Crear reemplaza la lista.\n'
                  'Se integra el área de cada fuente en los volúmenes de la grilla, incluso subnodo.',
                  justify='left').pack(anchor='w',pady=8)
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i,s in enumerate(self.sources):
            size=f'Ø {s.width:g}' if s.geometry=='Circular' else f'{s.width:g} × {s.height:g}'
            self.tree.insert('','end',iid=str(i),values=(s.geometry,f'({s.x:g}, {s.y:g})',size,f'{s.intensity:g}'))
        self.count.set(str(len(self.sources)))

    def create(self):
        try:
            n=int(self.count.get());lx,ly=self.dimensions()
            if not 0<=n<=256:
                raise ValueError('Cantidad entre 0 y 256')
            size=.4*min(lx/(n+1),ly)
            rows=[HeatSource((i+1)*lx/(n+1),ly/2,size) for i in range(n)]
        except (ValueError,OverflowError) as exc:
            messagebox.showerror('Fuentes inválidas',str(exc),parent=self);return
        self.sources=rows;self.refresh()

    def add(self):
        try:
            self.edit_source(template_source(*self.dimensions()),None)
        except (ValueError,OverflowError) as exc:
            messagebox.showerror('Fuente inválida',str(exc),parent=self)

    def edit(self):
        if self.tree.selection():
            index=int(self.tree.selection()[0]);self.edit_source(self.sources[index],index)

    def remove(self):
        if self.tree.selection():
            del self.sources[int(self.tree.selection()[0])];self.refresh()

    def edit_source(self,source,index):
        dialog=tk.Toplevel(self);dialog.title('Fuente constante');dialog.transient(self.winfo_toplevel())
        geometry=tk.StringVar(value=source.geometry)
        ttk.Label(dialog,text='Geometría').grid(row=0,column=0,padx=8,pady=6)
        combo=ttk.Combobox(dialog,values=GEOMETRIES,textvariable=geometry,state='readonly')
        combo.grid(row=0,column=1,padx=8,pady=6)
        entries={};widgets={}
        width_label=tk.StringVar(value='Lado (m)')
        for row,(key,label,value) in enumerate((('x','Centro X (m)',source.x),('y','Centro Y (m)',source.y),
                    ('width',None,source.width),('height','Alto (m)',source.height),
                    ('intensity','Intensidad Q (W/m³)',source.intensity)),1):
            if label is None:
                ttk.Label(dialog,textvariable=width_label).grid(row=row,column=0,padx=8,pady=5)
            else:
                ttk.Label(dialog,text=label).grid(row=row,column=0,padx=8,pady=5)
            entries[key]=tk.StringVar(value=str(value))
            widget=ttk.Entry(dialog,textvariable=entries[key]);widgets[key]=widget
            widget.grid(row=row,column=1,padx=8,pady=5)
        def change(event=None):
            width_label.set('Diámetro (m)' if geometry.get()=='Circular' else
                            'Ancho (m)' if geometry.get()=='Rectangular' else 'Lado (m)')
            widgets['height'].configure(state='normal' if geometry.get()=='Rectangular' else 'disabled')
        combo.bind('<<ComboboxSelected>>',change);change()
        def accept():
            try:
                values={key:float(var.get()) for key,var in entries.items()}
                if geometry.get()!='Rectangular':
                    values['height']=values['width']
                s=HeatSource(**values,geometry=geometry.get())
                from ..model.sources import validate_sources
                from ..model.grid import Grid
                lx,ly=self.dimensions();validate_sources((s,),Grid(lx=lx,ly=ly))
            except (ValueError,OverflowError) as exc:
                messagebox.showerror('Fuente inválida',str(exc),parent=dialog);return
            if index is None:
                self.sources.append(s)
            else:
                self.sources[index]=s
            self.refresh();dialog.destroy()
        ttk.Button(dialog,text='Aceptar fuente',command=accept).grid(row=6,column=1,pady=10)
        ttk.Button(dialog,text='Cancelar',command=dialog.destroy).grid(row=6,column=0,pady=10)
        return dialog
