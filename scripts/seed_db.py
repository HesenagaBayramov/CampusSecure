"""Run from the project root: python -m scripts.seed_db"""

from app import create_app
from app.db import seed_db


if __name__ == "__main__":
    with create_app().app_context():
        seed_db()
    print("Demo data seeded.")
