"""Selección y edición de fuentes/trazos del dominio, con portapapeles local."""
from dataclasses import replace
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk,messagebox
from ..model.sources import HeatSource,validate_sources
from ..model.domain import validate_domain
from .objects import bounds,hit,translated


class SelectionMixin:
    def init_selection(self):
        self.selection=None;self.clipboard_object=None;self._move_original=None
        self.object_menu=tk.Menu(self,tearoff=False,postcommand=self._object_actions)
        for text,command in (('Editar posición y tamaño…',self.edit_selected),
                ('Duplicar (Ctrl+D)',self.duplicate_selected),('Copiar (Ctrl+C)',self.copy_selected),
                ('Pegar (Ctrl+V)',self.paste_object),('Eliminar (Supr)',self.delete_selected)):
            self.object_menu.add_command(label=text,command=command)
        ttk.Menubutton(self.toolbar,text='Objeto ▾',menu=self.object_menu).pack(side='left',padx=3)
        self.canvas.bind('<Button-3>',self.popup_object)
        self.canvas.bind('<Double-Button-1>',lambda e:self.edit_selected())
        for sequence,command in (('<Control-c>',self.copy_selected),('<Control-v>',self.paste_object),
              ('<Control-d>',self.duplicate_selected),('<Delete>',self.delete_selected),
              ('<Control-z>',self.undo),('<Escape>',self.cancel_move)):
            self.canvas.bind(sequence,lambda e,f=command:(f(),'break')[1])
        for sequence,dx,dy in (('<Left>',-1,0),('<Right>',1,0),('<Up>',0,1),('<Down>',0,-1)):
            self.canvas.bind(sequence,lambda e,x=dx,y=dy:self.nudge(x,y,e))

    def _object_actions(self):
        for i in (0,1,2,4):self.object_menu.entryconfigure(i,state='normal' if self.selected() else 'disabled')
        self.object_menu.entryconfigure(3,state='normal' if self.clipboard_object else 'disabled')

    def object_list(self,target):return self.sources.sources if target=='sources' else self.edits

    def selected(self):
        if self.selection is None:return None
        target,obj=self.selection
        if not any(item is obj for item in self.object_list(target)):
            self.selection=None;return None
        return target,obj

    def select_at(self,x,y):
        target='sources' if self.group.get()=='Fuentes' else 'domain'
        self.selection=None
        for obj in reversed(self.object_list(target)):
            if hit(obj,x,y):self.selection=(target,obj);break
        self.redraw()
        return self.selected()

    def popup_object(self,event):
        self.canvas.focus_set();self.start=None;self._move_original=None
        self.select_at(*self.physical(event))
        self.object_menu.tk_popup(event.x_root,event.y_root)
        self.object_menu.grab_release()

    def draw_selection(self,obj=None,tag='selection'):
        self.canvas.delete(tag)
        selected=self.selected()
        if obj is None and selected is not None:obj=selected[1]
        if obj is None:return
        x0,x1,y0,y1=bounds(obj)
        self.canvas.create_rectangle(*self.screen(x0,y1),*self.screen(x1,y0),
                                    outline='#ffe16a',width=2,dash=(5,3),tags=tag)

    def selection_press(self,event):
        self.canvas.focus_set()
        found=self.select_at(*self.physical(event))
        self.start=self.physical(event) if found else None
        self._move_original=found[1] if found else None

    def selection_drag(self,event):
        if self.start is None or self._move_original is None:return
        x,y=self.physical(event)
        obj=translated(self._move_original,x-self.start[0],y-self.start[1],self.grid_value())
        self.draw_selection(obj,'gesture')

    def selection_release(self,event):
        if self.start is None or self._move_original is None:return
        original=self._move_original;x,y=self.physical(event)
        dx,dy=x-self.start[0],y-self.start[1]
        self.start=None;self._move_original=None;self.canvas.delete('gesture')
        try:self.replace_selected(translated(original,dx,dy,self.grid_value()))
        except ValueError as exc:messagebox.showerror('Movimiento inválido',str(exc),parent=self)
        self.redraw()

    def validate_objects(self,target,objects):
        if target=='sources':validate_sources(tuple(objects),self.grid_value())
        else:validate_domain(SimpleNamespace(grid=self.grid_value(),domain=replace(self.domain,edits=tuple(objects))))

    def commit_objects(self,target,objects,selected):
        self.validate_objects(target,objects)
        self.remember(target)
        if target=='sources':self.sources.sources=list(objects);self.sources.refresh()
        else:self.edits=list(objects)
        self.selection=(target,selected) if selected is not None else None
        self.redraw()

    def replace_selected(self,obj):
        found=self.selected()
        if found is None:return
        target,old=found
        if obj==old:return
        objects=[obj if item is old else item for item in self.object_list(target)]
        self.commit_objects(target,objects,obj)

    def copy_selected(self):
        found=self.selected()
        if found:self.clipboard_object=found

    def paste_object(self):
        if self.clipboard_object is None:return
        target,obj=self.clipboard_object;g=self.grid_value()
        try:
            copy=translated(obj,g.dx,g.dy,g)
            self.commit_objects(target,[*self.object_list(target),copy],copy)
            self.clipboard_object=(target,copy)
            self.tool.set('Seleccionar fuente' if target=='sources' else 'Seleccionar geometría')
        except ValueError as exc:messagebox.showerror('No se puede pegar',str(exc),parent=self)

    def duplicate_selected(self):
        if self.selected():self.copy_selected();self.paste_object()

    def delete_selected(self):
        found=self.selected()
        if found:
            target,obj=found
            try:self.commit_objects(target,[item for item in self.object_list(target) if item is not obj],None)
            except ValueError as exc:messagebox.showerror('No se puede eliminar',str(exc),parent=self)

    def nudge(self,dx,dy,event):
        found=self.selected()
        if found:
            g=self.grid_value();factor=.1 if event.state&1 else 1
            try:self.replace_selected(translated(found[1],dx*g.dx*factor,dy*g.dy*factor,g))
            except ValueError as exc:self.pointer.set(str(exc))
        return 'break'

    def cancel_move(self):
        self.start=None;self._move_original=None;self.canvas.delete('gesture');self.redraw()

    def edit_selected(self):
        found=self.selected()
        if found is None:return
        target,obj=found;x0,x1,y0,y1=bounds(obj)
        dialog=tk.Toplevel(self);dialog.title('Editar objeto seleccionado');dialog.transient(self.winfo_toplevel())
        values={'x':(x0+x1)/2,'y':(y0+y1)/2,'width':x1-x0,'height':y1-y0}
        if target=='sources':values['intensity']=obj.intensity
        labels={'x':'Centro X (m)','y':'Centro Y (m)','width':'Ancho / diámetro (m)',
                'height':'Alto (m)','intensity':'Q (W/m³)'}
        fields={}
        for row,(key,value) in enumerate(values.items()):
            if key=='height' and isinstance(obj,HeatSource) and obj.geometry!='Rectangular':continue
            ttk.Label(dialog,text=labels[key]).grid(row=row,column=0,padx=8,pady=5)
            var=tk.StringVar(value=str(value));fields[key]=var
            ttk.Entry(dialog,textvariable=var,width=20).grid(row=row,column=1,padx=8,pady=5)
        def apply():
            try:
                if self.selected()!=found:raise ValueError('La selección cambió; volver a abrir el editor del objeto')
                v={key:float(var.get()) for key,var in fields.items()}
                if target=='sources':
                    new=replace(obj,**v)
                    if obj.geometry!='Rectangular':new=replace(new,height=new.width)
                else:
                    new=replace(obj,xmin=v['x']-v['width']/2,xmax=v['x']+v['width']/2,
                                ymin=v['y']-v['height']/2,ymax=v['y']+v['height']/2)
                self.replace_selected(new);dialog.destroy()
            except (ValueError,OverflowError) as exc:messagebox.showerror('Valores inválidos',str(exc),parent=dialog)
        ttk.Button(dialog,text='Aplicar',command=apply).grid(row=len(values),column=1,pady=8)
        ttk.Button(dialog,text='Cancelar',command=dialog.destroy).grid(row=len(values),column=0,pady=8)
