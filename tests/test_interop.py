"""Prueba gráfica opt-in: ventana real, subprocess y timeout para evitar cuelgues."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np


@unittest.skipUnless(os.environ.get('YOGUI_TEST_GL') == '1',
                     'Activar YOGUI_TEST_GL=1 para abrir una ventana de prueba')
class InteropTests(unittest.TestCase):
    def test_shared_vbo_and_render(self):
        self.check_transport('shared')

    def test_host_transfer_and_render(self):
        self.check_transport('host')

    def test_auto_without_pyopencl_gl_support(self):
        self.check_transport('auto',mask_gl=True)

    def test_runtime_acquire_failure_recovers_without_reset(self):
        import pyopencl as cl
        if not cl.have_gl():
            self.skipTest('Se requiere sharing para inyectar fallo posterior')
        self.check_transport('auto',fail_late=True)

    def check_transport(self,mode,mask_gl=False,fail_late=False):
        import pyopencl as cl
        if mode=='shared' and not cl.have_gl():
            self.skipTest('PyOpenCL sin soporte GL')
        if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
            self.skipTest('Sin servidor gráfico')
        from yoguicuentas.compute.device import devices
        try:
            available = devices()
        except RuntimeError as exc:
            self.skipTest(str(exc))
        index = int(os.environ.get('YOGUI_TEST_DEVICE','0'))
        if not 0 <= index < len(available):
            self.fail('Índice de prueba fuera de rango')
        if mode=='shared' and 'cl_khr_gl_sharing' not in available[index].extensions.split():
            self.skipTest('Dispositivo sin cl_khr_gl_sharing')
        with tempfile.TemporaryDirectory() as directory:
            arguments=['--gui','--device',str(index),'--transfer',mode,
                       '--batch-size','8','--smoke-seconds','3','--output',directory]
            if fail_late:
                code="""import pyopencl as cl
original=cl.enqueue_acquire_gl_objects
calls=0
def acquire(*args,**kwargs):
    global calls
    calls+=1
    if calls==2:
        raise cl.LogicError('INVALID_OPERATION simulado tras inicialización')
    return original(*args,**kwargs)
cl.enqueue_acquire_gl_objects=acquire
from yoguicuentas.app import main
main()
"""
                command=[sys.executable,'-c',code,*arguments]
            elif mask_gl:
                code="import pyopencl as cl; cl.have_gl=lambda:False; from yoguicuentas.app import main; main()"
                command=[sys.executable,'-c',code,*arguments]
            else:
                command=[sys.executable,'-m','yoguicuentas',*arguments]
            subprocess.run(command,check=True,timeout=25,
                           cwd=Path(__file__).resolve().parents[1])
            report = json.loads((Path(directory)/'interop.json').read_text())
            self.assertEqual(report['errors'],[])
            self.assertEqual(report['transfer'],'shared' if mode=='shared' else 'host')
            if mask_gl:
                self.assertIsNotNone(report['transfer_reason'])
            self.assertEqual(report['grid_shape'],[31,47])
            self.assertEqual(report['sources'],1)
            self.assertEqual(report['regions'],1)
            self.assertEqual(report['interface_mean'],'Armónica')
            self.assertEqual(report['requested_speed'],.5)
            self.assertTrue(report['playback_not_ahead'])
            self.assertEqual(report['final_time'],.205)
            self.assertEqual(report['visible_time'],.205)
            self.assertTrue(report['finished'])
            self.assertEqual(report['ui_checks']['initial_steps'],0)
            for key in ('initial_paused','info_hidden','info_shown','button_started',
                        'reset_steps_zero','reset_visible_zero','reset_paused','screenshot_saved',
                        'configuration_applied','configuration_stopped','speed_selected','speed_preserved'):
                self.assertTrue(report['ui_checks'][key],key)
            for error in report['shader_linear_rgb_error'].values():
                self.assertLessEqual(error,5)
            from PIL import Image
            screenshot=Image.open(Path(directory)/'screenshot.png')
            metadata=json.loads(screenshot.info['YoguiCuentas'])
            self.assertEqual(metadata['step'],0)
            self.assertEqual(metadata['time_s'],0)
            self.assertGreater(screenshot.width,100)
            screenshot.close()
            self.assertIsNone(report['ui_checks']['screenshot_error'])
            self.assertEqual(len(report['modes']),5)
            for mode,checks in report['modes'].items():
                self.assertEqual(checks['gl_error'],0,mode)
                self.assertGreater(checks['pixel_std'],10,mode)
            from PIL import Image
            images=[np.asarray(Image.open(Path(directory)/f'mode_{i}.png'))
                    for i in range(5)]
            for a,b in ((0,1),(0,2),(2,3),(0,4)):
                self.assertGreater(np.mean(np.abs(images[a].astype(float)-images[b])),1)
            self.assertGreater(report['publications'],2)
            self.assertGreater(report['frames'],2)
            self.assertLess(report['cpu_vbo_linf_K'],.001)
            from PIL import Image
            pixels = np.asarray(Image.open(Path(directory)/'canvas.png'))
            self.assertGreater(np.std(pixels),10)
