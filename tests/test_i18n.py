"""Language changes must never alter physical settings or reset the run."""
import os
import unittest
from yoguicuentas.ui.i18n import tk, ttk, set_language, language, translate, add_language_menu

class CatalogueTests(unittest.TestCase):
    def tearDown(self): set_language('es')
    def test_spanish_default_and_numeric_status(self):
        self.assertEqual(language(), 'es')
        self.assertEqual(translate('Iniciar'), 'Iniciar')
        set_language('en')
        self.assertEqual(translate('Iniciar'), 'Start')
        self.assertEqual(translate('En ejecución · paso 128'), 'Running · step 128')
        self.assertEqual(translate('/home/usuario/material.json'), '/home/usuario/material.json')
        self.assertEqual(translate('Campo guardado: /tmp/Material/Fuentes.csv'), 'Field saved: /tmp/Material/Fuentes.csv')

@unittest.skipUnless(os.environ.get('YOGUI_TEST_GL') == '1', 'Graphical opt-in')
class LanguageUITests(unittest.TestCase):
    def setUp(self):
        set_language('es'); self.root=tk.Tk(); self.root.withdraw()
    def tearDown(self):
        self.root.destroy(); set_language('es')
    def test_menu_labels_status_and_canonical_choices(self):
        bar=tk.Menu(self.root); view=tk.Menu(bar); bar.add_cascade(label='Ver',menu=view)
        menu=add_language_menu(bar)
        value=tk.StringVar(self.root,value='Armónica')
        box=ttk.Combobox(self.root,textvariable=value,values=['Armónica','Aritmética'])
        status=tk.StringVar(self.root,value='Listo para iniciar')
        label=ttk.Label(self.root,textvariable=status)
        button=ttk.Button(self.root,text='Iniciar')
        menu.invoke(1); self.root.update_idletasks()
        self.assertEqual(bar.entrycget(1,'label'),'View')
        self.assertEqual(bar.entrycget(2,'label'),'Language')
        self.assertEqual(button.cget('text'),'Start')
        self.assertEqual(self.root.getvar(label.cget('textvariable')),'Ready to start')
        self.assertEqual(value.get(),'Armónica')
        self.assertEqual(box.get(),'Armónica')
        self.assertEqual(tuple(box.cget('values')),('Harmonic','Arithmetic'))
        box.current(1)
        self.assertEqual(value.get(),'Aritmética')
        self.assertEqual(box.get(),'Aritmética')
        status.set('Pausado'); button.configure(text='Reanudar')
        self.assertEqual(self.root.getvar(label.cget('textvariable')),'Paused')
        self.assertEqual(button.cget('text'),'Resume')
        menu.invoke(0)
        self.assertEqual(box.get(),'Aritmética')
        self.assertEqual(button.cget('text'),'Reanudar')
    def test_open_and_future_dialogs_and_notebook(self):
        window=tk.Toplevel(self.root);window.withdraw();window.title('Configurar nueva corrida')
        tabs=ttk.Notebook(window);frame=ttk.Frame(tabs);tabs.add(frame,text='Inicial')
        set_language('en')
        self.assertEqual(window.title(),'Configure a new run')
        self.assertEqual(tabs.tab(frame,'text'),'Initial state')
        later=tk.Toplevel(self.root);later.withdraw();later.title('Guardar lienzo')
        self.assertEqual(later.title(),'Save canvas')
        set_language('es')
        self.assertEqual(later.title(),'Guardar lienzo')

    def test_configuration_keeps_draft_and_applies_canonical_values_in_english(self):
        from yoguicuentas.config.scenarios import Scenario
        from yoguicuentas.ui.configuration import open_configuration
        from tkinter import ttk as native_ttk
        results=[]
        scenario=Scenario()
        dialog=open_configuration(self.root,scenario,results.append)
        def walk(parent):
            for child in parent.winfo_children():
                yield child
                yield from walk(child)
        combos=[w for w in walk(dialog) if isinstance(w,native_ttk.Combobox)]
        mean=next(w for w in combos if 'Armónica' in tuple(w.cget('values')))
        boundary=next(w for w in combos if 'Adiabático' in tuple(w.cget('values')))
        mean.set('Geométrica');boundary.set('Robin')
        boundary.event_generate('<<ComboboxSelected>>')
        set_language('en');self.root.update()
        self.assertEqual(mean.get(),'Geométrica')
        self.assertEqual(boundary.get(),'Robin')
        self.assertIn('Geometric',tuple(mean.cget('values')))
        self.assertIn('Adiabatic',tuple(boundary.cget('values')))
        apply=next(w for w in walk(dialog) if isinstance(w,native_ttk.Button) and w.cget('text')=='Apply and restart')
        apply.invoke()
        self.assertEqual(len(results),1)
        self.assertEqual(results[0].interface_mean,'Geométrica')
        self.assertEqual(results[0].left.kind,'Robin')
        self.assertEqual(scenario.interface_mean,'Armónica')
