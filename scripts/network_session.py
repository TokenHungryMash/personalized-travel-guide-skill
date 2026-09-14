"""Probe once; reuse an explicitly evidenced, workbench-local proxy setting."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from datetime import datetime, timezone
from _network_policy import PROXY_NETWORKS, address_allowed

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbench',type=Path)
    parser.add_argument('--check-host')
    parser.add_argument('--confirm-known-proxy',action='store_true')
    parser.add_argument('--evidence',default='')
    parser.add_argument('--run',nargs=argparse.REMAINDER)
    args=parser.parse_args();root=args.workbench.resolve();settings=root/'network-session.json'
    if args.run is not None:
        if not args.run: parser.error('--run requires a bundled script name')
        script=Path(__file__).resolve().parent/args.run[0]
        if script.parent.resolve()!=Path(__file__).resolve().parent or not script.is_file() or script.suffix!='.py':
            parser.error('--run accepts a script in this Skill scripts directory only')
        env=os.environ.copy()
        if settings.is_file():
            record=json.loads(settings.read_text(encoding='utf-8'))
            if record.get('allow_known_fake_ip') is True and record.get('evidence') and record.get('workbench')==str(root):
                env.setdefault('TRAVEL_GUIDE_ALLOW_FAKE_IP','1')
        timer=Path(__file__).with_name('timed_step.py')
        return subprocess.run([sys.executable,str(timer),str(root),script.name,*args.run[1:]],env=env).returncode
    if not args.check_host: parser.error('supply --check-host with one already selected official hostname, or --run')
    addresses=sorted({row[4][0] for row in socket.getaddrinfo(args.check_host,443,type=socket.SOCK_STREAM)})
    fake=any(any(ipaddress.ip_address(a) in net for net in PROXY_NETWORKS) for a in addresses)
    if args.confirm_known_proxy:
        if not fake or not args.evidence.strip(): parser.error('confirmation requires a known Fake-IP result and actual local proxy evidence')
        root.mkdir(parents=True,exist_ok=True)
        settings.write_text(json.dumps({'workbench':str(root),'allow_known_fake_ip':True,'evidence':args.evidence,'host':args.check_host,'addresses':addresses,'checked_at':datetime.now(timezone.utc).isoformat()},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'host':args.check_host,'addresses':addresses,'known_fake_ip':fake,'explicit_setting_saved':args.confirm_known_proxy,'allowed_now':[address_allowed(a,args.check_host) for a in addresses]},ensure_ascii=False))
    if fake: print('Known proxy DNS range is not proof of broken networking. Confirm actual local proxy evidence once; run subsequent bundled network commands through network_session.py <workbench> --run <script.py> <args>. TLS/private-address checks remain active. Do not rotate mirrors or retry a policy denial.')
    return 0

if __name__=='__main__':raise SystemExit(main())
