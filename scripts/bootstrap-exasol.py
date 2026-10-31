"""Bootstrap only a newly installed, private local Exasol Personal instance.

Credentials remain in ignored files; TLS fingerprint comes from trusted launcher state.
Existing independently configured users must be configured manually, not overwritten.
"""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import ssl
import hashlib
import pyexasol

parser = argparse.ArgumentParser()
parser.add_argument('deployment_info', type=Path, help='Trusted launcher deployment.json')
parser.add_argument('--certificate', type=Path, help='Certificate copied from trusted local container; never downloaded from an unverified connection')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
info = json.loads(args.deployment_info.read_text())
connection = info.get('connection', {})
fingerprint = connection.get('certFingerprint', '')
if args.certificate:
    certificate_der = ssl.PEM_cert_to_DER_cert(args.certificate.read_text())
    fingerprint = hashlib.sha256(certificate_der).hexdigest()
if not re.fullmatch('[a-fA-F0-9]{64}', fingerprint):
    raise SystemExit('Missing verified fingerprint in launcher state; configure TLS privately')
port = int(connection['dbPort'])
if not 1 <= port <= 65535:
    raise SystemExit('Invalid local database port')
dsn = f'127.0.0.1/{fingerprint}:{port}'
config_path = root / '.env'
if not config_path.exists():
    raise SystemExit('Run configure.py first')
config = dict(line.split('=', 1) for line in config_path.read_text().splitlines() if line and not line.startswith('#'))
if config.get('EXASOL_PASSWORD') != 'SET_PRIVATELY':
    raise SystemExit('Exasol is already configured; refusing to overwrite credentials')
private_path = root / '.runtime/exasol-bootstrap.json'
private_path.parent.mkdir(exist_ok=True)
recovering = private_path.exists()
private = json.loads(private_path.read_text()) if recovering else {'app': secrets.token_urlsafe(32), 'admin': secrets.token_urlsafe(32)}
try:
    launcher_secrets_path = args.deployment_info.with_name('secrets.json')
    launcher_secrets = json.loads(launcher_secrets_path.read_text())
    admin_password = os.getenv('EXASOL_BOOTSTRAP_PASSWORD', launcher_secrets['dbPassword'])
    conn = pyexasol.connect(dsn=dsn, user='sys', password=admin_password, encryption=True, connection_timeout=5, socket_timeout=15, autocommit=False)
    existing = conn.execute("SELECT COUNT(*) FROM EXA_DBA_USERS WHERE USER_NAME='ADVERGENT'").fetchval()
    if existing and not recovering:
        raise RuntimeError('Dedicated user exists; configure manually')
    private_path.write_text(json.dumps(private), encoding='utf-8')
    if not existing:
        conn.execute('CREATE USER ADVERGENT IDENTIFIED BY {password!q}', {'password': private['app']})
    conn.execute('GRANT CREATE SESSION, CREATE SCHEMA, CREATE TABLE TO ADVERGENT')
    conn.execute('ALTER USER SYS IDENTIFIED BY {password!q}', {'password': private['admin']})
    conn.commit()
    conn.close()
    config.update(EXASOL_DSN=dsn, EXASOL_USER='ADVERGENT', EXASOL_PASSWORD=private['app'])
    config_path.write_text(''.join(f'{key}={value}\n' for key, value in config.items()), encoding='utf-8')
    launcher_secrets['dbPassword'] = private['admin']
    launcher_secrets_path.write_text(json.dumps(launcher_secrets), encoding='utf-8')
except Exception:
    raise SystemExit('Bootstrap failed; inspect private configuration and preserve recovery credentials. No driver details logged.') from None
print('Dedicated Exasol user configured, initial admin password rotated, private environment updated.')
