"""Recuperación real de un venv incompleto, sin red ni instalaciones globales."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class EnvironmentTests(unittest.TestCase):
    def test_detect_missing_pip_and_repair_without_installing_requirements(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            venv=Path(directory)/'entorno'
            subprocess.run([sys.executable,'-m','venv','--without-pip',str(venv)],
                           check=True,timeout=20)
            environment={**os.environ,'YOGUI_VENV':str(venv),'YOGUI_PYTHON':sys.executable}
            result=subprocess.run(['bash',str(root/'ejecutar.sh'),'--list-devices'],
                                  env=environment,capture_output=True,text=True,timeout=15)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('pip',result.stderr)
            subprocess.run(['bash',str(root/'instalar.sh'),'--preparar-entorno'],
                           env=environment,check=True,capture_output=True,text=True,timeout=30)
            subprocess.run([str(venv/'bin/python'),'-m','pip','--version'],
                           check=True,capture_output=True,timeout=10)
            result=subprocess.run(['bash',str(root/'ejecutar.sh'),'--list-devices'],
                                  env=environment,capture_output=True,text=True,timeout=15)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('requisitos',result.stderr)
