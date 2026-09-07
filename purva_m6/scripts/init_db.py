from alembic.config import Config
from alembic import command

if __name__ == "__main__":
    command.upgrade(Config("alembic.ini"), "head")
    print("M6 database migrated to head.")
