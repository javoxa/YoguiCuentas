#!/usr/bin/env python3
"""Check English paper provenance and unchanged equations/numerical data."""
from pathlib import Path
import hashlib
import json
import re

root=Path(__file__).resolve().parents[1]
control=json.loads((root/'technical_report/control_documental_en.json').read_text())
es=(root/control['source_spanish']).read_text()
en=(root/control['translation']).read_text()
def numeric_columns(text):
    return [re.findall(r'(?<![A-Za-z])\d+(?:\.\d+)?(?:e[-+]?\d+)?',line.split('&',1)[1])
            for line in text.splitlines() if re.match(r'[^&]* & [0-9]',line)]
def coordinates(text):
    return re.findall(r'\\addplot[^\n]*coordinates[^\n]*',text)
def equations(text):
    return re.findall(r'\\begin\{(equation|align)\}(.*?)\\end\{\1\}',text,re.S)
if numeric_columns(es)!=numeric_columns(en):raise SystemExit('Numerical table columns differ')
if coordinates(es)!=coordinates(en):raise SystemExit('Plot coordinates differ')
if equations(es)!=equations(en):raise SystemExit('Equations differ')
for name,expected in control['sha256'].items():
    if hashlib.sha256((root/name).read_bytes()).hexdigest()!=expected:
        raise SystemExit('Document hash changed: '+name)
print('English paper verified: source/PDF hashes, equations, plot coordinates and numerical columns')
