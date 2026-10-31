"""Generate local-only config without printing secrets. Existing config is preserved."""
import sys
import secrets
import argparse
from getpass import getpass
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from advergent.security import hash_password

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--generate', action='store_true', help='Save generated operator password to ignored .runtime/operator-password.txt without displaying it')
args = parser.parse_args()
if (root / '.env').exists():
    raise SystemExit('.env exists; edit it privately instead of overwriting')
password = secrets.token_urlsafe(24) if args.generate else getpass('Choose demo operator password (at least 12 characters): ')
if len(password) < 12:
    raise SystemExit('Password too short')
pg_password = secrets.token_urlsafe(32)
(root / '.env').write_text(
    f'DATABASE_URL=postgresql+psycopg://advergent:{pg_password}@127.0.0.1:5432/advergent\n'
    f'POSTGRES_PASSWORD={pg_password}\nOPERATOR_PASSWORD_HASH={hash_password(password)}\n'
    'EXASOL_DSN=127.0.0.1:8563\nEXASOL_USER=ADVERGENT\nEXASOL_PASSWORD=SET_PRIVATELY\n'
    'COOKIE_SECURE=false\nAPP_ORIGIN=http://127.0.0.1:8000\n', encoding='utf-8')
if args.generate:
    (root / '.runtime').mkdir(exist_ok=True)
    (root / '.runtime/operator-password.txt').write_text(password, encoding='utf-8')
print('Created ignored .env. Set verified Exasol credentials privately.')
