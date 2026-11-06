"""Localised Tk presentation with canonical model values kept in Spanish.

No global tkinter monkey-patching: only this application's UI imports the facade.
Labels and read-only choices refresh in place; simulation state is unaffected.
"""
import re
import weakref
import tkinter as _tk
from tkinter import ttk as _ttk, messagebox as _messagebox, filedialog as _filedialog, simpledialog as _simpledialog
from .translations import EN

_language = 'es'
_widgets = weakref.WeakSet()

def language():
    return _language

def translate(text):
    if _language == 'es' or not isinstance(text, str):
        return text
    if text in EN:
        return EN[text]
    # Dynamic status lines use the same catalogue, preserving numbers and paths.
    return ''.join(part if i % 2 else _pattern.sub(lambda m: EN[m.group()], part)
                   for i, part in enumerate(_paths.split(text)))

_paths = re.compile(r'(https?://\S+|(?:/|~/)[^\s]+)')

_pattern = re.compile('|'.join(r'(?<!\w)' + re.escape(k) + r'(?!\w)' for k in sorted(EN, key=len, reverse=True) if k))

def set_language(value):
    global _language
    if value not in ('es', 'en'):
        raise ValueError('Unsupported language')
    _language = value
    for widget in list(_widgets):
        try:
            if widget.winfo_exists(): widget._refresh_language()
        except _tk.TclError:
            _widgets.discard(widget)

class LocalText:
    def __init__(self, *args, **kwargs):
        self._original_text = kwargs.get('text')
        self._source_var = None
        self._display_var = None
        self._var_trace = None
        if self._original_text is not None:
            kwargs['text'] = translate(self._original_text)
        source = kwargs.get('textvariable')
        super().__init__(*args, **kwargs)
        _widgets.add(self)
        if source is not None and isinstance(self, (_ttk.Label, _ttk.Button, _ttk.Checkbutton)):
            self._source_var = source
            self._display_var = _tk.StringVar(master=self)
            self._var_trace = source.trace_add('write', lambda *_: self._refresh_language())
            super().configure(textvariable=self._display_var)
            self._refresh_language()
        self.bind('<Destroy>', self._remove_trace, add='+')

    def _remove_trace(self, event):
        if event.widget is self and self._var_trace is not None:
            self._source_var.trace_remove('write', self._var_trace)
            self._var_trace = None

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}; cnf = None
        if 'text' in kwargs:
            self._original_text = kwargs['text']
            kwargs['text'] = translate(kwargs['text'])
        return super().configure(cnf, **kwargs)
    config = configure

    def _refresh_language(self):
        if self._original_text is not None:
            super().configure(text=translate(self._original_text))
        if self._source_var is not None:
            self._display_var.set(translate(self._source_var.get()))

class Combobox(_ttk.Combobox):
    def __init__(self, master=None, **kwargs):
        self._choices = tuple(kwargs.pop('values', ()))
        self._canonical = kwargs.pop('textvariable', None) or _tk.StringVar(master=master)
        self._display = _tk.StringVar(master=master)
        self._syncing = False
        super().__init__(master, textvariable=self._display, values=[translate(x) for x in self._choices], **kwargs)
        self._canonical_trace = self._canonical.trace_add('write', self._from_model)
        self._display_trace = self._display.trace_add('write', self._from_display)
        _widgets.add(self)
        self.bind('<Destroy>', self._cleanup, add='+')
        self._refresh_language()

    def _cleanup(self, event):
        if event.widget is self:
            self._canonical.trace_remove('write', self._canonical_trace)
            self._display.trace_remove('write', self._display_trace)

    def _from_model(self, *_):
        if not self._syncing:
            self._syncing = True
            try: self._display.set(translate(self._canonical.get()))
            finally: self._syncing = False

    def _from_display(self, *_):
        if not self._syncing:
            value = self._display.get()
            canonical = next((x for x in self._choices if translate(x) == value), value)
            self._syncing = True
            try: self._canonical.set(canonical)
            finally: self._syncing = False

    def _refresh_language(self):
        super().configure(values=[translate(x) for x in self._choices])
        self._from_model()

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict): kwargs = {**cnf, **kwargs}; cnf = None
        if 'values' in kwargs:
            self._choices = tuple(kwargs['values'])
            kwargs['values'] = [translate(x) for x in self._choices]
        return super().configure(cnf, **kwargs)
    config = configure
    def get(self): return self._canonical.get()
    def set(self, value): self._canonical.set(value)

class Menu(_tk.Menu):
    def __init__(self, *a, **kw):
        self._labels = {}
        super().__init__(*a, **kw); _widgets.add(self)
    def add(self, itemType, cnf=None, **kw):
        options = {**(cnf or {}), **kw}
        label = options.get('label')
        if label is not None: options['label'] = translate(label)
        super().add(itemType, **options)
        if label is not None: self._labels[self.index('end')] = label
    def entryconfigure(self, index, cnf=None, **kw):
        if cnf is None and not kw: return super().entryconfigure(index)
        options = {**(cnf or {}), **kw}
        if 'label' in options:
            self._labels[self.index(index)] = options['label']
            options['label'] = translate(options['label'])
        return super().entryconfigure(index, **options)
    entryconfig = entryconfigure
    def delete(self, first, last=None):
        start = self.index(first); stop = self.index(first if last is None else last)
        result = super().delete(first, last)
        if start is not None and stop is not None:
            self._labels = {(i if i < start else i-(stop-start+1)): text
                            for i, text in self._labels.items() if i < start or i > stop}
        return result
    def _refresh_language(self):
        for index, label in self._labels.items(): super().entryconfigure(index, label=translate(label))

class Notebook(_ttk.Notebook):
    def __init__(self, *a, **kw):
        self._tab_text = {}; super().__init__(*a, **kw); _widgets.add(self)
    def add(self, child, **kw):
        if 'text' in kw:
            self._tab_text[str(child)] = kw['text']; kw['text'] = translate(kw['text'])
        return super().add(child, **kw)
    def _refresh_language(self):
        for tab, text in self._tab_text.items():
            if tab in self.tabs(): super().tab(tab, text=translate(text))

class Treeview(_ttk.Treeview):
    def __init__(self, *a, **kw):
        self._heading_text = {}; super().__init__(*a, **kw); _widgets.add(self)
    def heading(self, column, option=None, **kw):
        if 'text' in kw:
            self._heading_text[column] = kw['text']; kw['text'] = translate(kw['text'])
        return super().heading(column, option, **kw)
    def _refresh_language(self):
        for column, text in self._heading_text.items(): super().heading(column, text=translate(text))

class WindowText:
    def __init__(self, *a, **kw):
        self._original_title = ''; super().__init__(*a, **kw); _widgets.add(self)
    def title(self, value=None):
        if value is None: return super().title()
        self._original_title = value
        return super().title(translate(value))
    wm_title = title
    def _refresh_language(self): super().title(translate(self._original_title))

class Facade:
    def __init__(self, module, **overrides): self._module = module; self.__dict__.update(overrides)
    def __getattr__(self, name): return getattr(self._module, name)

# Keep input widgets and canonical variables untouched.
tk = Facade(_tk, Tk=type('Tk', (WindowText, _tk.Tk), {}), Toplevel=type('Toplevel', (WindowText, _tk.Toplevel), {}), Menu=Menu)
ttk = Facade(_ttk, Combobox=Combobox, Notebook=Notebook, Treeview=Treeview,
            **{name: type(name, (LocalText, getattr(_ttk, name)), {})
               for name in ('Label', 'LabelFrame', 'Button', 'Checkbutton', 'Radiobutton')})

def _dialog(module, name):
    original = getattr(module, name)
    def call(*args, **kwargs):
        args = tuple(translate(x) if i < 2 else x for i, x in enumerate(args))
        for key in ('title', 'message', 'prompt', 'detail'):
            if key in kwargs: kwargs[key] = translate(kwargs[key])
        if 'filetypes' in kwargs:
            kwargs['filetypes'] = [(translate(label), pattern) for label, pattern in kwargs['filetypes']]
        return original(*args, **kwargs)
    return call

messagebox = Facade(_messagebox, **{n: _dialog(_messagebox, n) for n in ('showinfo', 'showwarning', 'showerror', 'askyesno', 'askokcancel', 'askyesnocancel', 'askretrycancel')})
filedialog = Facade(_filedialog, **{n: _dialog(_filedialog, n) for n in ('askopenfilename', 'asksaveasfilename', 'askdirectory')})
simpledialog = Facade(_simpledialog, **{n: _dialog(_simpledialog, n) for n in ('askfloat', 'askinteger', 'askstring')})

def add_language_menu(menubar):
    menu = Menu(menubar, tearoff=False)
    selected = _tk.StringVar(master=menubar, value=language())
    for label, value in [('Español', 'es'), ('English', 'en')]:
        menu.add_radiobutton(label=label, value=value, variable=selected,
                             command=lambda: set_language(selected.get()))
    menubar.add_cascade(label='Idioma', menu=menu)
    menu._language_selection = selected
    return menu
