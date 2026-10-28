"""Ventanas acotadas a pantalla y formularios desplazables con acciones fijas."""
import tkinter as tk
from tkinter import ttk,font as tkfont


def fit_window(window,width,height,parent=None):
    # Reservar espacio para decoraciones, paneles y barra de tareas (incluido HD).
    sw,sh=window.winfo_screenwidth(),window.winfo_screenheight()
    width=min(width,max(320,sw-64));height=min(height,max(240,sh-112))
    x=max(16,(sw-width)//2);y=max(24,(sh-height)//2-16)
    if parent is not None and parent.winfo_ismapped():
        x=max(16,min(sw-width-16,parent.winfo_rootx()+(parent.winfo_width()-width)//2))
        y=max(24,min(sh-height-64,parent.winfo_rooty()+(parent.winfo_height()-height)//2))
    window.geometry(f'{width}x{height}+{x}+{y}')
    window.minsize(min(720,width),min(420,height))
    return width,height


class ScrollablePage(ttk.Frame):
    def __init__(self,parent):
        super().__init__(parent)
        self.content=None;self._bound=set()
        self.rowconfigure(0,weight=1);self.columnconfigure(0,weight=1)
        self.canvas=tk.Canvas(self,highlightthickness=0,width=1,height=1)
        self.canvas.grid(row=0,column=0,sticky='nsew')
        self.vertical=ttk.Scrollbar(self,orient='vertical',command=self.canvas.yview)
        self.horizontal=ttk.Scrollbar(self,orient='horizontal',command=self.canvas.xview)
        self.vertical.grid(row=0,column=1,sticky='ns')
        self.horizontal.grid(row=1,column=0,sticky='ew')
        self.canvas.configure(yscrollcommand=self.vertical.set,xscrollcommand=self.horizontal.set)
        self.canvas.bind('<Configure>',self._layout)
        self.bind('<Destroy>',self._destroyed,add='+')

    def set_content(self,content):
        if content.master is not self.canvas:
            raise ValueError('El contenido desplazable debe ser hijo directo de su canvas')
        self.content=content
        self.window=self.canvas.create_window(0,0,window=content,anchor='nw')
        content.bind('<Configure>',self._layout,add='+')

    def _destroyed(self,event):
        if event.widget==self:self._bound.clear()

    def _layout(self,event=None):
        if self.content is None:return
        w,h=max(1,self.canvas.winfo_width()),max(1,self.canvas.winfo_height())
        rw,rh=self.content.winfo_reqwidth(),self.content.winfo_reqheight()
        self.canvas.itemconfigure(self.window,width=max(w,rw),height=max(h,rh))
        self.canvas.configure(scrollregion=(0,0,max(w,rw),max(h,rh)))
        if rh>h+1:self.vertical.grid()
        else:self.vertical.grid_remove();self.canvas.yview_moveto(0)
        if rw>w+1:self.horizontal.grid()
        else:self.horizontal.grid_remove();self.canvas.xview_moveto(0)
        self._bind_content(self.content)

    def _bind_content(self,widget):
        if str(widget) not in self._bound:
            self._bound.add(str(widget))
            for event in ('<MouseWheel>','<Button-4>','<Button-5>'):
                widget.bind(event,self._wheel,add='+')
            widget.bind('<FocusIn>',self._reveal,add='+')
        for child in widget.winfo_children():self._bind_content(child)

    def _wheel(self,event):
        # Mantener el desplazamiento propio de listas y selectores.
        if event.widget.winfo_class() in ('TCombobox','Treeview','Text','Listbox'):return
        if self.canvas.yview()==(0.0,1.0) or event.state&0x100:return
        units=(-1 if event.num==4 else 1) if event.num in (4,5) else (-1 if event.delta>0 else 1)
        self.canvas.yview_scroll(units*3,'units')
        return 'break'

    def _reveal(self,event):
        widget=event.widget
        if widget==self.content or not widget.winfo_ismapped():return
        top=widget.winfo_rooty()-self.content.winfo_rooty()
        bottom=top+widget.winfo_height()
        visible=self.canvas.canvasy(0);height=self.canvas.winfo_height()
        total=max(height,self.content.winfo_height())
        if top<visible:self.canvas.yview_moveto(max(0,(top-8)/total))
        elif bottom>visible+height:self.canvas.yview_moveto(max(0,(bottom-height+8)/total))


class ScrollableNotebook(ttk.Notebook):
    """Notebook con scroll independiente por sección; expone las páginas originales."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.pages={};self.contents={}
        self._style=ttk.Style(self)
        self._style_name=f'Settings{id(self)}.TNotebook'
        self._tab_layout=self._style.layout('TNotebook.Tab')
        self.configure(style=self._style_name)
        self.section_bar=ttk.Frame(self.master)
        ttk.Label(self.section_bar,text='Sección:').pack(side='left',padx=5)
        self.section=tk.StringVar(self)
        self.section_choice=ttk.Combobox(self.section_bar,textvariable=self.section,state='readonly',width=30)
        self.section_choice.pack(side='left',padx=5,pady=4)
        self.section_choice.bind('<<ComboboxSelected>>',self._choose_section)
        self.bind('<Configure>',self._navigation,add='+')
        self.bind('<<NotebookTabChanged>>',self._selected_section,add='+')
        self._compact=None

    def page(self,factory=ttk.Frame,*args,**kwargs):
        """Construir la página dentro del canvas para respetar el apilado de Tk."""
        page=ScrollablePage(self)
        child=factory(page.canvas,*args,**kwargs)
        page.set_content(child)
        self.pages[str(child)]=page;self.contents[str(page)]=str(child)
        return child

    def add(self,child,**kwargs):
        if str(child) not in self.pages:
            raise ValueError('Crear las páginas con notebook.page(...) antes de agregarlas')
        super().add(self.pages[str(child)],**kwargs)

    def _navigation(self,event=None):
        tabs=self.tabs()
        if not tabs:return
        labels=[self.tab(tab,'text') for tab in tabs]
        self.section_choice.configure(values=labels)
        font=tkfont.nametofont('TkDefaultFont',root=self)
        required=sum(font.measure(label)+24 for label in labels)
        compact=required>self.winfo_width()-8
        if compact!=self._compact:
            self._compact=compact
            self._style.layout(self._style_name+'.Tab',[] if compact else self._tab_layout)
            if compact:self.section_bar.pack(fill='x',padx=10,before=self)
            else:self.section_bar.pack_forget()
        self._selected_section()

    def _choose_section(self,event=None):
        index=self.section_choice.current()
        if index>=0:self.select(self.tabs()[index])

    def _selected_section(self,event=None):
        selected=self.select()
        if selected:self.section.set(self.tab(selected,'text'))

    def _page(self,tab):return self.pages.get(str(tab),tab)

    def tabs(self):return tuple(self.contents.get(tab,tab) for tab in super().tabs())

    def select(self,tab_id=None):
        if tab_id is not None:return super().select(self._page(tab_id))
        selected=super().select()
        return self.contents.get(selected,selected)

    def tab(self,tab_id,option=None,**kwargs):return super().tab(self._page(tab_id),option,**kwargs)

    def index(self,tab_id):return super().index(self._page(tab_id))
