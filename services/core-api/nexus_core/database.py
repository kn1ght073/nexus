"""Database engine and session management.

SQLite with WAL + foreign keys for the local node; PostgreSQL when
NEXUS_DATABASE_URL is set (hosted control plane on Render + Neon/Supabase
free tiers). Postgres enforces foreign keys natively and needs no pragmas.
"""
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .settings import get_settings

settings = get_settings()


def _engine_url() -> str:
    if settings.database_url:
        url = settings.database_url
        # Render/Neon/Supabase dashboards hand out postgres:// or
        # postgresql+psycopg2:// interchangeably; SQLAlchemy's psycopg2
        # driver accepts either, but normalize the bare scheme anyway.
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    return f"sqlite:///{settings.database_path}"


engine = create_engine(
    _engine_url(),
    # SQLite only: allow multiple threads (FastAPI runs sync handlers in a
    # threadpool). Harmless for Postgres URLs.
    connect_args={"check_same_thread": False} if not settings.database_url else {},
    # Free-tier Postgres closes idle connections aggressively; recycle so
    # pooled connections don't go stale between requests.
    pool_pre_ping=True,
    pool_recycle=300,
)


# WAL mode gives concurrent readers while a writer is active (multiple
# clients hitting the API at once); foreign keys must be enabled per
# connection in SQLite.
if not settings.database_url:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
