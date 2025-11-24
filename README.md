dev start:
```
poetry install
PYTHONPATH=src poetry run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

database initialization:
```
PYTHONPATH=src poetry run python init_db.py
```