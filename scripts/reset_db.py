"""Run from the project root: python -m scripts.reset_db"""

from app import create_app
from app.db import reset_db


if __name__ == "__main__":
    with create_app().app_context():
        reset_db()
    print("Demo data reset.")
