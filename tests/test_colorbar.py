import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
from yoguicuentas.render.colorbar import ColorScale,active_scale,colormap,legend_image


class ColorbarTests(unittest.TestCase):
    def test_scale_matches_displayed_quantity(self):
        r=SimpleNamespace(lower=-10,upper=90,gradient_upper=12,flux_upper=340)
        for mode,title,unit,low,high in ((0,'Temperatura','°C',-10,90),(1,'Temperatura','°C',-10,90),
                  (2,'|∇T|','K/m',0,12),(3,'|q|','W/m²',0,340),(4,'Temperatura','°C',-10,90)):
            r.mode=mode
            self.assertEqual(active_scale(r),ColorScale(title,unit,low,high))

    def test_legend_uses_same_colormap_and_increasing_values(self):
        np.testing.assert_allclose(colormap([0,.5,1]),[[.08,.16,.55],[.05,.85,.65],[1,.25,.04]])
        image=np.asarray(legend_image(ColorScale('Temperatura','°C',-10,90),148,400))
        np.testing.assert_allclose(image[58,20,:3],np.rint(colormap(1)*255),atol=1)
        np.testing.assert_allclose(image[370,20,:3],np.rint(colormap(0)*255),atol=1)
        with self.assertRaises(ValueError):legend_image(ColorScale('T','°C',10,10),148,400)

    @unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
    def test_menu_toggle_modes_reconfigure_and_png(self):
        code=r'''
import tkinter as tk,time,json
from pathlib import Path
from dataclasses import replace
import numpy as np
from OpenGL import GL
from PIL import Image
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.render.canvas import HeatCanvas
from yoguicuentas.render.colorbar import active_scale,legend_image
from yoguicuentas.ui.view_menu import add_view_menu
root=tk.Tk();errors=[];calls=[]
canvas=HeatCanvas(root,Scenario(),int(__import__('os').environ.get('YOGUI_TEST_DEVICE','0')),32,
                  lambda c:None,errors.append,transfer='host',width=640,height=480)
menubar=tk.Menu(root,tearoff=False);menubar.add_cascade(label='Archivo',menu=tk.Menu(menubar,tearoff=False))
view,visible=add_view_menu(menubar,canvas,lambda:calls.append('scale'));root.configure(menu=menubar)
assert menubar.entrycget(1,'label')=='Ver'
assert not visible.get();view.invoke(0);assert visible.get() and canvas.colorbar_visible
canvas.pack(fill='both',expand=True)
deadline=time.monotonic()+10
while time.monotonic()<deadline:
    root.update();time.sleep(.002)
    assert not errors,errors
    if canvas.initialized and canvas.frames>1:break
else:raise AssertionError('No inició el lienzo')
assert canvas.renderer.show_colorbar and canvas.controller.paused
canvas.tkMakeCurrent();r=canvas.renderer
r.lower=-10;r.upper=90;r.gradient_upper=12;r.flux_upper=340
for mode in range(5):
    r.mode=mode;r.draw(canvas.interop.vbo,canvas.width,canvas.height)
    assert r.colorbar.key[0]==active_scale(r)
    scale=active_scale(r);strip=r.colorbar.width(canvas.width)
    expected=legend_image(scale,strip,canvas.height)
    x=canvas.width-strip+20;y=canvas.height//2
    pixel=np.frombuffer(GL.glReadPixels(x,y,1,1,GL.GL_RGB,GL.GL_UNSIGNED_BYTE),dtype=np.uint8)
    np.testing.assert_allclose(pixel,np.array(expected)[canvas.height-1-y,20,:3],atol=1)
    assert GL.glGetError()==GL.GL_NO_ERROR
    key=r.colorbar.key;r.draw(canvas.interop.vbo,canvas.width,canvas.height)
    assert r.colorbar.key is key  # texture cache hit; no regeneration per frame
# A colour-limit edit refreshes the legend without changing the simulated field.
r.mode=4;r.lower=10;r.upper=40;r.draw(canvas.interop.vbo,canvas.width,canvas.height)
assert r.colorbar.key[0].lower==10 and r.colorbar.key[0].upper==40
view.invoke(2);assert calls==['scale']
path=Path(__import__('sys').argv[1]);canvas.capture.request(path)
deadline=time.monotonic()+5
while time.monotonic()<deadline:
    root.update();time.sleep(.002)
    if canvas.capture.result:break
else:raise AssertionError('No se guardó la captura')
with Image.open(path) as im:
    metadata=json.loads(im.info['YoguiCuentas'])
    assert metadata['colorbar'] is True
    assert np.std(np.asarray(im)[:,-strip:])>10
# Visibility survives a new scenario; menu and rendering remain synchronized.
canvas.configure_scenario(replace(canvas.scenario,amplitude=20))
deadline=time.monotonic()+5
while canvas.pending_scenario is not None and time.monotonic()<deadline:
    root.update();time.sleep(.002)
assert canvas.pending_scenario is None and canvas.renderer.show_colorbar
view.invoke(0);assert not visible.get() and not canvas.renderer.show_colorbar
root.update();assert not errors,errors
canvas.close();root.destroy()
'''
        with tempfile.TemporaryDirectory() as folder:
            path=Path(os.environ.get('YOGUI_COLORBAR_OUTPUT',folder))/ 'barra_colores.png'
            path.parent.mkdir(parents=True,exist_ok=True)
            result=subprocess.run([sys.executable,'-c',code,str(path)],capture_output=True,text=True,timeout=25)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
