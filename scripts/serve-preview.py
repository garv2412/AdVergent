"""UI/auth-denial smoke preview only. Deliberately unreachable databases."""
import secrets
import uvicorn
from advergent.api import create_app
from advergent.config import Settings
from advergent.security import hash_password

settings = Settings('postgresql+psycopg://unused@127.0.0.1:1/unused', hash_password(secrets.token_urlsafe(32)), '127.0.0.1:1', 'unused', 'unused', 'http://127.0.0.1:8000', False)
uvicorn.run(create_app(settings), host='127.0.0.1', port=8000)
