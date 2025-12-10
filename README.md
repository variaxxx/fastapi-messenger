dependencies installation:
```
poetry install
```

dev start:
```
poetry run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

linting:
```
poetry run ruff check --fix
```

database initialization:
```
PYTHONPATH=src poetry run python init_db.py
```