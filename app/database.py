import logging
import os
import ssl

from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

# Host substrings that almost always mean "public managed Postgres → TLS required"
_MANAGED_PG_SSL_HOST_HINTS = (
    "rlwy.net",  # Railway Postgres proxy (*.proxy.rlwy.net)
    "railway.app",
    "neon.tech",
    "supabase.co",
    "render.com",
)


def _host_suggests_managed_ssl(host: str | None) -> bool:
    if not host:
        return False
    h = host.lower()
    if h in ("localhost", "127.0.0.1", "::1"):
        return False
    return any(marker in h for marker in _MANAGED_PG_SSL_HOST_HINTS)


def _prepare_async_engine():
    """Build engine URL + asyncpg connect_args.

    Managed Postgres (Railway, Neon, etc.) usually requires TLS. asyncpg does not use
    libpq's sslmode query param the same way — we pass ssl= via connect_args and strip
    sslmode from the URL to avoid ambiguous failures that surface as 500s on every request.
    """
    url = make_url(settings.database_url)
    connect_args: dict = {}
    q = dict(url.query) if url.query else {}
    sslmode = (q.get("sslmode") or "").lower()
    explicit = settings.database_ssl

    def strip_sslmode(u):
        if not u.query or "sslmode" not in u.query:
            return u
        return u.set(
            query={k: v for k, v in u.query.items() if k != "sslmode"}
        )

    use_ssl = False
    if explicit is True:
        use_ssl = True
    elif explicit is False:
        use_ssl = False
    elif sslmode in ("require", "verify-ca", "verify-full"):
        use_ssl = True
    elif os.environ.get("PGSSLMODE", "").lower() in (
        "require",
        "verify-full",
        "verify-ca",
    ):
        use_ssl = True
    elif q.get("ssl") in ("true", "1", "True"):
        use_ssl = True
    elif _host_suggests_managed_ssl(url.host):
        # Railway often omits sslmode in DATABASE_URL; asyncpg still needs ssl= in connect_args
        use_ssl = True
        logger.info("Postgres host %s looks like a managed provider — enabling TLS", url.host)

    if use_ssl:
        connect_args["ssl"] = ssl.create_default_context()
        url = strip_sslmode(url)
    elif explicit is False:
        # User disabled SSL; strip sslmode from URL so asyncpg does not see conflicting hints
        url = strip_sslmode(url)

    return url, connect_args


_url_obj, _connect_args = _prepare_async_engine()

engine = create_async_engine(
    _url_obj,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args if _connect_args else {},
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        logger.exception(
            "Database initialization failed. Check DATABASE_URL, SSL (set DATABASE_SSL=true "
            "on Railway if needed), and that Postgres has the pgvector extension available."
        )
        raise
