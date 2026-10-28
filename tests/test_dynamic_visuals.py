import os
from pathlib import Path
import subprocess
import sys
import unittest
import numpy as np
from yoguicuentas.render.isotherms import contour_levels
from yoguicuentas.render.colorbar import ColorScale,zoom_scale


class DynamicVisualTests(unittest.TestCase):
    def test_levels_and_mouse_zoom(self):
        np.testing.assert_allclose(contour_levels(10,70,5),[20,30,40,50,60])
        self.assertEqual(len(contour_levels(25,25,10)),0)
        lo,hi=zoom_scale(ColorScale('T','°C',10,70),.25,2)
        self.assertEqual(hi-lo,30);self.assertEqual(lo+.25*(hi-lo),25)
        self.assertEqual(zoom_scale(ColorScale('q','W/m²',0,80),.5,2),(0,40))

    @unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
    def test_actual_curve_count_labels_auto_scale_and_mouse(self):
        code=r'''
import time,tkinter as tk
from types import SimpleNamespace
import numpy as np
from OpenGL import GL
from PIL import Image
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.render.canvas import HeatCanvas
root=tk.Tk();errors=[]
canvas=HeatCanvas(root,Scenario(),int(__import__('os').environ.get('YOGUI_TEST_DEVICE','1')),8,
                  lambda c:None,errors.append,transfer='host',width=640,height=480)
canvas.pack(fill='both',expand=True)
end=time.monotonic()+10
while time.monotonic()<end:
    root.update();time.sleep(.002)
    assert not errors,errors
    if canvas.initialized and canvas.frames>1:break
else:raise AssertionError('No inició')
canvas.tkMakeCurrent();r=canvas.renderer
x,y=r.grid.coordinates();linear=np.ascontiguousarray(100*x/r.grid.lx,dtype=np.float32)
probe=int(GL.glGenBuffers(1));GL.glBindBuffer(GL.GL_ARRAY_BUFFER,probe)
GL.glBufferData(GL.GL_ARRAY_BUFFER,linear.nbytes,linear,GL.GL_DYNAMIC_DRAW)
r.show_vectors=False;r.show_isotherms=True;r.auto_scale=True
for count in (1,5,12,20,30):
    r.isotherm_count=count;r.show_isotherm_labels=False
    r.draw(probe,640,480)
    np.testing.assert_allclose(r.field_stats[:2],(0,100),atol=1e-5)
    np.testing.assert_allclose((r.lower,r.upper),(0,100),atol=1e-5)
    # Count distinct rendered curves, not just the parameter or metadata.
    row=np.frombuffer(GL.glReadPixels(80,240,480,1,GL.GL_RGB,GL.GL_UNSIGNED_BYTE),dtype=np.uint8).reshape(-1,3)
    white=np.all(row>225,axis=1)
    runs=int(white[0])+int(np.count_nonzero(white[1:]&~white[:-1]))
    assert runs==count,('Cantidad real de líneas',count,runs)
# Contours follow the field even if the colour scale deliberately excludes it.
r.auto_scale=False;r.lower=-100;r.upper=500;r.isotherm_count=7
r.draw(probe,640,480)
plain=np.frombuffer(GL.glReadPixels(0,0,640,480,GL.GL_RGB,GL.GL_UNSIGNED_BYTE),dtype=np.uint8).copy()
r.show_isotherm_labels=True
r.draw(probe,640,480)
assert r.isotherms.label_count==7,r.isotherms.last_anchors
np.testing.assert_allclose(r.isotherms.last_anchors[:,3],np.arange(1,8)*12.5,atol=2e-5)
labelled=np.frombuffer(GL.glReadPixels(0,0,640,480,GL.GL_RGB,GL.GL_UNSIGNED_BYTE),dtype=np.uint8).copy()
assert np.count_nonzero(plain!=labelled)>100
folder=__import__('os').environ.get('YOGUI_VISUAL_OUTPUT')
if folder:
    from pathlib import Path
    Path(folder).mkdir(parents=True,exist_ok=True)
    Image.fromarray(labelled.reshape(480,640,3)[::-1]).save(Path(folder)/'isotermas_7_rotuladas.png')
for mode in (1,2,3):
    r.mode=mode;r.draw(probe,640,480)
    assert r.isotherms.label_count>0 and GL.glGetError()==GL.GL_NO_ERROR
# Mouse over the legend edits scale rather than orbiting the 3D surface.
r.mode=1;r.show_colorbar=True;r.auto_scale=True;r.draw(probe,canvas.width,canvas.height)
yaw,pitch=r.yaw,r.pitch;span=r.upper-r.lower
canvas.wheel(SimpleNamespace(num=4,delta=0,x=canvas.width-20,y=canvas.height//2))
assert not r.auto_scale and r.upper-r.lower<span
assert (r.yaw,r.pitch)==(yaw,pitch)
old=r.upper
canvas.start_drag(SimpleNamespace(x=canvas.width-20,y=55))
canvas.drag(SimpleNamespace(x=canvas.width-20,y=35));canvas.end_drag(None)
assert r.upper>old
canvas.fit_from_legend(SimpleNamespace(x=canvas.width-20,y=55));assert r.fit_requested
r.draw(probe,canvas.width,canvas.height);assert r.upper==100 and r.lower==0
# A constant field has no invented contour lines or labels.
GL.glBindBuffer(GL.GL_ARRAY_BUFFER,probe)
GL.glBufferSubData(GL.GL_ARRAY_BUFFER,0,linear.nbytes,np.full_like(linear,42))
r.auto_scale=True;r.draw(probe,canvas.width,canvas.height)
assert r.lower<42<r.upper and len(r.isotherms.last_levels)==0 and r.isotherms.label_count==0
assert GL.glGetError()==GL.GL_NO_ERROR and canvas.scheduler.steps==0
GL.glDeleteBuffers(1,[probe]);canvas.close();root.destroy()
'''
        result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],
                              capture_output=True,text=True,timeout=35)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
