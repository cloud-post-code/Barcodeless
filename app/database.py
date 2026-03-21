import logging
import os
import ssl

from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ProgrammingError
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
    "amazonaws.com",  # RDS / many managed providers
    "azure.com",
    "aiven.io",
    "elephantsql.com",
    "digitalocean.com",
    "cockroachlabs.cloud",
)


def _host_never_auto_ssl(host: str | None) -> bool:
    """Private / docker-style hosts where TLS is normally off."""
    if not host:
        return False
    h = host.lower()
    if h in ("localhost", "127.0.0.1", "::1"):
        return True
    # Private service discovery (Railway, k8s, docker compose)
    if h.endswith(".internal"):
        return True
    # Typical compose service name: postgres, db (no FQDN)
    if "." not in h:
        return True
    return False


def _host_suggests_managed_ssl(host: str | None) -> bool:
    if not host or _host_never_auto_ssl(host):
        return False
    h = host.lower()
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
    elif sslmode == "disable":
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
    # asyncpg does not follow libpq sslmode; avoid leaving it in the URL.
    url = strip_sslmode(url)

    logger.info(
        "Postgres: host=%s database=%s tls=%s",
        url.host,
        url.database,
        "on" if connect_args.get("ssl") else "off",
    )

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
    except ProgrammingError:
        logger.exception(
            "Database initialization failed (SQL). If this mentions extension \"vector\", "
            "provision Postgres with pgvector (Railway: enable pgvector / use a pgvector image) "
            "or run CREATE EXTENSION vector as a superuser in the DB console."
        )
        raise
    except Exception:
        logger.exception(
            "Database initialization failed. Check DATABASE_URL, TLS (set DATABASE_SSL=true "
            "if your provider requires SSL and host was not auto-detected), and Railway "
            "service linking so DATABASE_URL points at your Postgres."
        )
        raise
