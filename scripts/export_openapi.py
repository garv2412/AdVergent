import json
from pathlib import Path
from advergent.api import create_app
from advergent.config import Settings

# Construction only; no connection or credentials needed to generate contracts.
settings = Settings('postgresql+psycopg://unused@localhost/unused', '', '', '', '', 'http://127.0.0.1:8000', False)
Path('openapi.json').write_text(json.dumps(create_app(settings).openapi(), indent=2) + '\n')
