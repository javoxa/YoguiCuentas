#!/usr/bin/env python3
"""Create a source snapshot for GitHub/Mac transfer without credentials or Git metadata."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import zipfile

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--name',default='Yogui_Cuentas_fuentes_20261106')
args=parser.parse_args()
if Path(args.name).name!=args.name or not args.name:raise SystemExit('Use a simple archive name')
for command in [['python3','scripts/sincronizar_traducciones.py','--check'],
                ['python3','technical_report/verificar_traduccion.py']]:
    subprocess.run(command,cwd=root,check=True)
listed=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=root)
files=sorted({Path(name.decode()) for name in listed.split(b'\0') if name})
manifest={}
for relative in files:
    source=root/relative
    if not source.exists():continue  # Deletions are represented by their absence.
    if source.is_symlink():raise SystemExit('Review symlink before packaging: '+str(relative))
    if any(part in ('.git','.venv','dist','metal_test_00','__pycache__') for part in relative.parts):
        raise SystemExit('Excluded directory unexpectedly listed: '+str(relative))
    if relative.name=='.env' or relative.suffix in ('.pem','.key'):
        raise SystemExit('Review potential credential file: '+str(relative))
    if source.stat().st_size>=100*1024*1024:raise SystemExit('GitHub file limit: '+str(relative))
    manifest[relative.as_posix()]=hashlib.sha256(source.read_bytes()).hexdigest()
out=root/'dist';out.mkdir(exist_ok=True)
archive=out/(args.name+'.zip')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as bundle:
    for name in manifest:bundle.write(root/name,root.name+'/'+name)
    bundle.writestr(root.name+'/MANIFIESTO_SINCRONIZACION.json',json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix('.zip.sha256').write_text(checksum+'  '+archive.name+'\n')
print(f'{archive}: {len(manifest)} files; SHA-256 {checksum}')
