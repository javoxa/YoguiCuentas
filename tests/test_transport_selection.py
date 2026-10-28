from unittest.mock import patch,MagicMock
import unittest
import numpy as np
from yoguicuentas.render.interop import create_transport


class TransportSelectionTests(unittest.TestCase):
    def test_auto_falls_back_when_acquire_fails_after_buffer_creation(self):
        failed=MagicMock()
        host=MagicMock()
        initial=np.zeros((3,3),dtype=np.float32)
        with patch('yoguicuentas.render.interop.shared_context'), \
             patch('yoguicuentas.render.interop.SharedTemperature',return_value=failed), \
             patch('yoguicuentas.render.interop.HostTemperature',return_value=host), \
             patch('yoguicuentas.render.interop.GL.glFinish'), \
             patch('yoguicuentas.render.interop.cl.CommandQueue'), \
             patch('yoguicuentas.render.interop.cl.Context'), \
             patch('yoguicuentas.render.interop.select_device'), \
             patch('yoguicuentas.render.interop.cl.enqueue_acquire_gl_objects',
                   side_effect=RuntimeError('INVALID_OPERATION'),create=True):
            _,transport,reason=create_transport(0,initial,'auto')
            self.assertIs(transport,host)
            self.assertIn('INVALID_OPERATION',reason)
            failed.close.assert_called_once()

    def test_explicit_shared_reports_acquire_failure(self):
        failed=MagicMock()
        with patch('yoguicuentas.render.interop.shared_context'), \
             patch('yoguicuentas.render.interop.SharedTemperature',return_value=failed), \
             patch('yoguicuentas.render.interop.GL.glFinish'), \
             patch('yoguicuentas.render.interop.cl.CommandQueue'), \
             patch('yoguicuentas.render.interop.cl.enqueue_acquire_gl_objects',
                   side_effect=RuntimeError('INVALID_OPERATION'),create=True):
            with self.assertRaisesRegex(RuntimeError,'--transfer host'):
                create_transport(0,np.zeros((3,3)), 'shared')
            failed.close.assert_called_once()
