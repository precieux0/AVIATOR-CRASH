from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Boolean
from .config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    verified = Column(Boolean, default=False)
    session_file = Column(String, nullable=True)
    # Subscription and preferences
    subscribed = Column(Boolean, default=False)
    language = Column(String, default='en')
    preferred_sites = Column(String, nullable=True)

class Observation(Base):
    __tablename__ = "observations"
    id = Column(Integer, primary_key=True, index=True)
    site = Column(String, index=True, nullable=True)
    odds = Column(String, nullable=True)
    multiplier = Column(String, nullable=True)
    ts = Column(Integer, nullable=False)


class SiteBlacklist(Base):
    __tablename__ = "site_blacklist"
    id = Column(Integer, primary_key=True, index=True)
    site = Column(String, unique=True, index=True, nullable=False)
    fail_count = Column(Integer, default=0)
    blacklisted_until = Column(Integer, nullable=True)
    last_failure_ts = Column(Integer, nullable=True)


class AdminAlert(Base):
    __tablename__ = "admin_alerts"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(String, nullable=False)
    ts = Column(Integer, nullable=False)
    sent = Column(Boolean, default=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
