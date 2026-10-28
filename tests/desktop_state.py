"""Native pointer hit-testing is unavailable behind the desktop lock screen."""
import os
import subprocess


def desktop_locked():
    session=os.environ.get('XDG_SESSION_ID')
    if not session:return False
    try:
        result=subprocess.run(['loginctl','show-session',session,'-p','LockedHint','--value'],
                              capture_output=True,text=True,timeout=2)
    except (OSError,subprocess.TimeoutExpired):return False
    return result.returncode==0 and result.stdout.strip()=='yes'
