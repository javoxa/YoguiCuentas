from unittest.mock import patch
import unittest
from yoguicuentas import launcher


class LauncherTests(unittest.TestCase):
    def test_console_does_not_choose_gpu(self):
        with patch('yoguicuentas.app.main') as app,patch.object(launcher,'choose_device') as choose:
            launcher.main(['--console','--backend','numpy','--steps','3'])
            choose.assert_not_called()
            app.assert_called_once_with(['--backend','numpy','--steps','3'])

    def test_list_does_not_open_window(self):
        with patch('yoguicuentas.app.main') as app,patch.object(launcher,'choose_device') as choose:
            launcher.main(['--list-devices'])
            choose.assert_not_called()
            app.assert_called_once_with(['--list-devices'])

    def test_explicit_and_selected_indices_are_forwarded(self):
        with patch('pyopencl.have_gl',return_value=True),patch('yoguicuentas.app.main') as app:
            with patch.object(launcher,'choose_device',return_value=7) as choose:
                launcher.main(['--device','2','--scenario','demo.json'])
                choose.assert_not_called()
                app.assert_called_once_with(['--gui','--device','2','--scenario','demo.json'])
                app.reset_mock()
                launcher.main([])
                app.assert_called_once_with(['--gui','--device','7'])

    def test_cancel_does_not_start_app(self):
        with patch('pyopencl.have_gl',return_value=True),patch('yoguicuentas.app.main') as app:
            with patch.object(launcher,'choose_device',return_value=None):
                launcher.main([])
                app.assert_not_called()

    def test_no_gl_support_does_not_block_host_gui(self):
        with patch('pyopencl.have_gl',return_value=False),patch('yoguicuentas.app.main') as app:
            launcher.main(['--device','3','--transfer','host'])
            app.assert_called_once_with(['--gui','--device','3','--transfer','host'])

    def test_single_igpu_without_sharing_is_selectable(self):
        from types import SimpleNamespace
        import pyopencl as cl
        device=SimpleNamespace(type=cl.device_type.GPU,extensions='')
        with patch('yoguicuentas.compute.device.devices',return_value=[device]):
            self.assertEqual(launcher.choose_device(),0)
