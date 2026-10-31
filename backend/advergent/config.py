import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    password_hash: str
    exasol_dsn: str
    exasol_user: str
    exasol_password: str
    origin: str
    cookie_secure: bool

    @classmethod
    def from_env(cls):
        return cls(
            os.environ['DATABASE_URL'], os.environ['OPERATOR_PASSWORD_HASH'],
            os.environ['EXASOL_DSN'], os.environ['EXASOL_USER'],
            os.environ['EXASOL_PASSWORD'], os.getenv('APP_ORIGIN', 'http://127.0.0.1:8000'),
            os.getenv('COOKIE_SECURE', 'true').lower() == 'true',
        )
