import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()  # reads variables from a .env file in the project root, if present

# Render (and most PaaS platforms) provide a single DATABASE_URL connection
# string for managed Postgres, rather than separate host/user/password vars.
# Prefer that if it's set; otherwise fall back to the DB_* vars used for
# local/Docker dev. Render's URLs sometimes use the "postgres://" scheme,
# which SQLAlchemy's psycopg2 driver doesn't recognize -- normalize to
# "postgresql://".
_database_url = os.getenv("DATABASE_URL")

if _database_url:
    if _database_url.startswith("postgres://"):
        _database_url = _database_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URL = _database_url
else:
    # Reads connection details from environment variables (set these in a .env
    # file or your shell/OS environment - see .env.example for the expected
    # keys). Falls back to sensible local-dev defaults if not set.
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "trafficvision")

    # URL-encode the password: special characters like @, :, / in a raw password
    # break the connection string format (user:password@host), since those
    # characters double as URL delimiters. quote_plus escapes them safely so a
    # password like "ankit@123" doesn't get misparsed as part of the hostname.
    DB_PASSWORD_ENCODED = quote_plus(DB_PASSWORD)

    SQLALCHEMY_DATABASE_URL = (
        f"postgresql://{DB_USER}:{DB_PASSWORD_ENCODED}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency used in route handlers to get a DB session per-request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
