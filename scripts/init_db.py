from core.config import settings
from core.storage import SQLiteStore


if __name__ == "__main__":
    store = SQLiteStore(settings.db_path)
    print(f"EcoPilot database initialized at {store.path}")
