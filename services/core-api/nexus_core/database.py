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
    s = get_settings()
    if s.control_plane_mode and not s.database_url and not s.allow_ephemeral_db:
        raise RuntimeError(
            "NEXUS_DATABASE_URL is required when running in control-plane mode. "
            "Refusing to silently use ephemeral SQLite."
        )
    if s.database_url:
        url = s.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    db_path = s.resolved_database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


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
