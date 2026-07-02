# Lottery Tracker — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the monorepo, Dockerized Postgres, a running FastAPI backend, the complete database schema via Alembic, and seeded game/prize reference data — the foundation every later plan builds on.

**Architecture:** A monorepo with `backend/` (FastAPI + SQLAlchemy 2.0 + Alembic) and `frontend/` (scaffolded later in Plan 7). `docker-compose.yml` runs Postgres and the backend. All persistent domain tables are defined now so later plans only add logic, not schema churn. Games and prize rules are **seeded reference data** (data, not code) so rule changes are a seed edit.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.0 (typed), Alembic, Pydantic v2 + pydantic-settings, psycopg 3, PostgreSQL 16, pytest + httpx, Docker Compose.

## Global Constraints

- **Python 3.12**; all backend code typed (SQLAlchemy 2.0 `Mapped[...]` style).
- **Money is integer cents** everywhere — never floats for money.
- **UUID primary keys** on every table (Postgres `gen_random_uuid()` default).
- **CORS in dev allows all origins** — env-driven (`CORS_ALLOW_ORIGINS`, default `*`) so a phone and a laptop on the LAN can both hit the API.
- **Games/prize rules are seeded reference data**, keyed by stable string `key`/`tier_key`.
- **Draw times are U.S. Central Time**; store dates as `date`, periods as an enum for Daily 4.
- **Tests run against Postgres** (schema uses Postgres arrays/JSONB) — a dedicated test database, not SQLite.
- **Frequent commits** — one per task minimum, following the steps.

---

### Task 1: Monorepo scaffold, Docker Compose, and backend health endpoint

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_health.py`
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `backend/.env.example`
- Modify: `.gitignore` (already exists)

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `app.config.Settings` — pydantic-settings model with `database_url: str`, `cors_allow_origins: list[str]` (parsed from comma-separated env `CORS_ALLOW_ORIGINS`, default `["*"]`), `get_settings()` cached accessor.
  - `app.main.app` — FastAPI instance with CORS middleware and `GET /api/health` → `{"status": "ok"}`.

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "lotto-tracker-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy>=2.0.30",
    "alembic>=1.13",
    "psycopg[binary]>=3.2",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2",
    "httpx>=0.27",
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `backend/app/config.py`**

```python
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://lotto:lotto@localhost:5432/lotto"
    cors_allow_origins: list[str] = ["*"]

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Lottery Tracker API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 4: Write the failing test — `backend/tests/test_health.py`**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 5: Create empty `backend/app/__init__.py` and `backend/tests/__init__.py`** (both empty files).

- [ ] **Step 6: Install deps and run the test to verify it passes**

Run:
```bash
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]" && pytest tests/test_health.py -v
```
Expected: PASS (`test_health_ok`).

- [ ] **Step 7: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 8: Create `backend/.env.example`**

```bash
DATABASE_URL=postgresql+psycopg://lotto:lotto@db:5432/lotto
CORS_ALLOW_ORIGINS=*
```

- [ ] **Step 9: Create `docker-compose.yml`** (repo root)

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: lotto
      POSTGRES_PASSWORD: lotto
      POSTGRES_DB: lotto
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lotto"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+psycopg://lotto:lotto@db:5432/lotto
      CORS_ALLOW_ORIGINS: "*"
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
```

- [ ] **Step 10: Verify the stack boots**

Run:
```bash
docker compose up -d db backend && sleep 8 && curl -s http://localhost:8000/api/health
```
Expected: `{"status":"ok"}`.

- [ ] **Step 11: Commit**

```bash
git add backend docker-compose.yml && git commit -m "feat: monorepo scaffold, docker compose, health endpoint"
```

---

### Task 2: Database session and Alembic setup

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `app.config.get_settings`.
- Produces:
  - `app.models.base.Base` — SQLAlchemy `DeclarativeBase` subclass; **all models import from here**.
  - `app.db.engine`, `app.db.SessionLocal` — engine + sessionmaker bound to `settings.database_url`.
  - `app.db.get_db()` — FastAPI dependency yielding a `Session`.
  - pytest fixture `db_session` (in conftest) — a `Session` on a dedicated test DB with tables created and rolled back per test.

- [ ] **Step 1: Create `backend/app/models/base.py`**

```python
import uuid

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime


class Base(DeclarativeBase):
    pass


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, server_default=func.gen_random_uuid())
```

- [ ] **Step 2: Create `backend/app/db.py`**

```python
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: Initialize Alembic**

Run:
```bash
cd backend && alembic init migrations
```
Then replace the generated `alembic.ini` `sqlalchemy.url` line with a placeholder (URL comes from env in `env.py`):
```ini
sqlalchemy.url =
```

- [ ] **Step 4: Edit `backend/migrations/env.py`** — wire it to settings + `Base.metadata`. Replace the config/target_metadata section with:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.models.base import Base
import app.models  # noqa: F401  ensures all models are imported/registered

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"),
                      target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 5: Create `backend/app/models/__init__.py`** (empty for now; models added in later tasks are imported here so Alembic autogenerate sees them).

```python
# Import all model modules here so Alembic's metadata is complete.
```

- [ ] **Step 6: Create the test DB fixture — `backend/tests/conftest.py`**

```python
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.base import Base
import app.models  # noqa: F401  register all models

# Derive a sibling test database URL from the configured one.
_base_url = get_settings().database_url
TEST_URL = _base_url.rsplit("/", 1)[0] + "/lotto_test"


@pytest.fixture(scope="session")
def engine():
    admin = create_engine(_base_url.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS lotto_test"))
        conn.execute(text("CREATE DATABASE lotto_test"))
    admin.dispose()
    eng = create_engine(TEST_URL)
    with eng.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        conn.commit()
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine):
    conn = engine.connect()
    txn = conn.begin()
    Session = sessionmaker(bind=conn, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        txn.rollback()
        conn.close()
```

Note: `gen_random_uuid()` requires the `pgcrypto` extension (created in the fixture; the first real migration will also create it for the app DB).

- [ ] **Step 7: Write a smoke test — `backend/tests/test_db.py`**

```python
from sqlalchemy import text


def test_db_session_connects(db_session):
    assert db_session.execute(text("SELECT 1")).scalar() == 1
```

- [ ] **Step 8: Run the test to verify it passes**

Run:
```bash
cd backend && . .venv/bin/activate && pytest tests/test_db.py -v
```
Expected: PASS (requires `docker compose up -d db` running).

- [ ] **Step 9: Commit**

```bash
git add backend && git commit -m "feat: db session + alembic + test db fixture"
```

---

### Task 3: Reference tables — games and prize_rules

**Files:**
- Create: `backend/app/models/reference.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_reference_models.py`

**Interfaces:**
- Consumes: `app.models.base.Base`, `uuid_pk`.
- Produces:
  - `Game` model — columns: `id` (UUID PK), `key` (str, unique), `display_name` (str), `main_count` (int), `main_min` (int), `main_max` (int), `has_special_ball` (bool), `special_min` (int|None), `special_max` (int|None), `base_price_cents` (int), `prize_type` (str: `fixed`|`pari_mutuel`|`mixed`), `draw_schedule` (JSONB dict).
  - `PrizeRule` model — columns: `id` (UUID PK), `game_id` (FK→games.id), `tier_key` (str), `match_main` (int), `match_special` (bool), `play_type` (str|None), `base_amount_cents` (int|None), `notes` (str|None). Unique on `(game_id, tier_key, play_type)`.

- [ ] **Step 1: Create `backend/app/models/reference.py`**

```python
import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, uuid_pk


class Game(Base):
    __tablename__ = "games"

    id: Mapped[uuid.UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String, unique=True, index=True)
    display_name: Mapped[str]
    main_count: Mapped[int]
    main_min: Mapped[int]
    main_max: Mapped[int]
    has_special_ball: Mapped[bool] = mapped_column(default=False)
    special_min: Mapped[int | None] = mapped_column(default=None)
    special_max: Mapped[int | None] = mapped_column(default=None)
    base_price_cents: Mapped[int]
    prize_type: Mapped[str]
    draw_schedule: Mapped[dict] = mapped_column(JSONB, default=dict)

    prize_rules: Mapped[list["PrizeRule"]] = relationship(back_populates="game")


class PrizeRule(Base):
    __tablename__ = "prize_rules"
    __table_args__ = (UniqueConstraint("game_id", "tier_key", "play_type"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id"))
    tier_key: Mapped[str]
    match_main: Mapped[int]
    match_special: Mapped[bool] = mapped_column(default=False)
    play_type: Mapped[str | None] = mapped_column(default=None)
    base_amount_cents: Mapped[int | None] = mapped_column(default=None)
    notes: Mapped[str | None] = mapped_column(default=None)

    game: Mapped["Game"] = relationship(back_populates="prize_rules")
```

- [ ] **Step 2: Register models — edit `backend/app/models/__init__.py`**

```python
# Import all model modules here so Alembic's metadata is complete.
from app.models import reference  # noqa: F401
```

- [ ] **Step 3: Write the failing test — `backend/tests/test_reference_models.py`**

```python
from app.models.reference import Game, PrizeRule


def test_game_and_prize_rule_persist(db_session):
    game = Game(
        key="powerball", display_name="Powerball", main_count=5,
        main_min=1, main_max=69, has_special_ball=True, special_min=1,
        special_max=26, base_price_cents=200, prize_type="fixed",
        draw_schedule={"days": ["Mon", "Wed", "Sat"], "time": "21:59"},
    )
    db_session.add(game)
    db_session.flush()
    rule = PrizeRule(game_id=game.id, tier_key="match5", match_main=5,
                     match_special=False, base_amount_cents=100_000_000)
    db_session.add(rule)
    db_session.flush()
    assert game.id is not None
    assert rule.game.key == "powerball"
    assert game.prize_rules[0].tier_key == "match5"
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
cd backend && . .venv/bin/activate && pytest tests/test_reference_models.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat: games + prize_rules reference models"
```

---

### Task 4: Domain tables — users, invites, tickets, play_lines, draws, ticket_results, ingestion_runs

**Files:**
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/ticket.py`
- Create: `backend/app/models/draw.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_domain_models.py`

**Interfaces:**
- Consumes: `Base`, `uuid_pk`, `Game`.
- Produces (exact model names + key columns later plans rely on):
  - `User(id, email UNIQUE, password_hash, display_name, role['user'|'admin'], created_at)`
  - `Invite(id, email, token UNIQUE, invited_by FK→users.id, expires_at, accepted_at|None)`
  - `Ticket(id, user_id FK→users.id, game_id FK→games.id, purchase_date, image_path|None, entry_method['manual'|'ocr'], ocr_confidence|None, add_ons JSONB, num_draws, total_cost_cents, created_at)`
  - `PlayLine(id, ticket_id FK→tickets.id, line_index, main_numbers int[], special_number|None, play_type|None, wager_cents, is_quick_pick)`
  - `Draw(id, game_id FK→games.id, draw_date, draw_period|None, winning_main int[], winning_special|None, multiplier|None, payouts JSONB|None, source['csv'|'scrape'|'manual'], ingested_at)` — UNIQUE `(game_id, draw_date, draw_period)`
  - `TicketResult(id, play_line_id FK→play_lines.id, draw_id FK→draws.id, match_main_count, match_special, tier_key|None, amount_won_cents, status['pending'|'won'|'no_win'], computed_at)`
  - `IngestionRun(id, game_id FK→games.id, status, rows_added, errors|None, ran_at)`

- [ ] **Step 1: Create `backend/app/models/user.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str]
    display_name: Mapped[str]
    role: Mapped[str] = mapped_column(default="user")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str]
    token: Mapped[str] = mapped_column(String, unique=True, index=True)
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime]
    accepted_at: Mapped[datetime | None] = mapped_column(default=None)
```

- [ ] **Step 2: Create `backend/app/models/ticket.py`**

```python
import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer

from app.models.base import Base, uuid_pk


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id"))
    purchase_date: Mapped[date]
    image_path: Mapped[str | None] = mapped_column(default=None)
    entry_method: Mapped[str] = mapped_column(default="manual")
    ocr_confidence: Mapped[float | None] = mapped_column(default=None)
    add_ons: Mapped[dict] = mapped_column(JSONB, default=dict)
    num_draws: Mapped[int] = mapped_column(default=1)
    total_cost_cents: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    play_lines: Mapped[list["PlayLine"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )


class PlayLine(Base):
    __tablename__ = "play_lines"

    id: Mapped[uuid.UUID] = uuid_pk()
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    line_index: Mapped[int]
    main_numbers: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    special_number: Mapped[int | None] = mapped_column(default=None)
    play_type: Mapped[str | None] = mapped_column(default=None)
    wager_cents: Mapped[int] = mapped_column(default=0)
    is_quick_pick: Mapped[bool] = mapped_column(default=False)

    ticket: Mapped["Ticket"] = relationship(back_populates="play_lines")
```

- [ ] **Step 3: Create `backend/app/models/draw.py`**

```python
import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class Draw(Base):
    __tablename__ = "draws"
    __table_args__ = (UniqueConstraint("game_id", "draw_date", "draw_period"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id"), index=True)
    draw_date: Mapped[date] = mapped_column(index=True)
    draw_period: Mapped[str | None] = mapped_column(default=None)
    winning_main: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    winning_special: Mapped[int | None] = mapped_column(default=None)
    multiplier: Mapped[int | None] = mapped_column(default=None)
    payouts: Mapped[dict | None] = mapped_column(JSONB, default=None)
    source: Mapped[str] = mapped_column(default="csv")
    ingested_at: Mapped[datetime] = mapped_column(server_default=func.now())


class TicketResult(Base):
    __tablename__ = "ticket_results"

    id: Mapped[uuid.UUID] = uuid_pk()
    play_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("play_lines.id", ondelete="CASCADE"), index=True
    )
    draw_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("draws.id"), index=True)
    match_main_count: Mapped[int] = mapped_column(default=0)
    match_special: Mapped[bool] = mapped_column(default=False)
    tier_key: Mapped[str | None] = mapped_column(default=None)
    amount_won_cents: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(default="pending")
    computed_at: Mapped[datetime] = mapped_column(server_default=func.now())


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id"))
    status: Mapped[str]
    rows_added: Mapped[int] = mapped_column(default=0)
    errors: Mapped[str | None] = mapped_column(default=None)
    ran_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

- [ ] **Step 4: Register models — edit `backend/app/models/__init__.py`**

```python
# Import all model modules here so Alembic's metadata is complete.
from app.models import reference  # noqa: F401
from app.models import user  # noqa: F401
from app.models import ticket  # noqa: F401
from app.models import draw  # noqa: F401
```

- [ ] **Step 5: Write the failing test — `backend/tests/test_domain_models.py`**

```python
from datetime import date, datetime, timedelta

from app.models.reference import Game
from app.models.user import User, Invite
from app.models.ticket import Ticket, PlayLine
from app.models.draw import Draw, TicketResult, IngestionRun


def _game(db):
    g = Game(key="lotto_texas", display_name="Lotto Texas", main_count=6,
             main_min=1, main_max=54, base_price_cents=100, prize_type="pari_mutuel",
             draw_schedule={"days": ["Mon", "Wed", "Sat"]})
    db.add(g); db.flush(); return g


def test_ticket_with_lines_and_result(db_session):
    g = _game(db_session)
    user = User(email="a@b.com", password_hash="x", display_name="A")
    db_session.add(user); db_session.flush()

    ticket = Ticket(user_id=user.id, game_id=g.id, purchase_date=date(2026, 7, 1),
                    num_draws=2, total_cost_cents=200,
                    play_lines=[PlayLine(line_index=0, main_numbers=[1, 2, 3, 4, 5, 6],
                                         wager_cents=100)])
    db_session.add(ticket); db_session.flush()
    assert ticket.play_lines[0].main_numbers == [1, 2, 3, 4, 5, 6]

    draw = Draw(game_id=g.id, draw_date=date(2026, 7, 2),
                winning_main=[1, 2, 3, 9, 10, 11], source="csv")
    db_session.add(draw); db_session.flush()

    res = TicketResult(play_line_id=ticket.play_lines[0].id, draw_id=draw.id,
                       match_main_count=3, tier_key="match3",
                       amount_won_cents=300, status="won")
    db_session.add(res); db_session.flush()
    assert res.status == "won"


def test_draw_unique_constraint(db_session):
    import pytest
    from sqlalchemy.exc import IntegrityError
    g = _game(db_session)
    db_session.add(Draw(game_id=g.id, draw_date=date(2026, 7, 2), winning_main=[1]))
    db_session.flush()
    db_session.add(Draw(game_id=g.id, draw_date=date(2026, 7, 2), winning_main=[2]))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_invite_and_ingestion_run(db_session):
    g = _game(db_session)
    admin = User(email="admin@b.com", password_hash="x", display_name="Admin", role="admin")
    db_session.add(admin); db_session.flush()
    inv = Invite(email="new@b.com", token="tok123", invited_by=admin.id,
                 expires_at=datetime.utcnow() + timedelta(days=7))
    run = IngestionRun(game_id=g.id, status="success", rows_added=3)
    db_session.add_all([inv, run]); db_session.flush()
    assert inv.accepted_at is None and run.rows_added == 3
```

- [ ] **Step 6: Run the tests to verify they pass**

Run:
```bash
cd backend && . .venv/bin/activate && pytest tests/test_domain_models.py -v
```
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add backend && git commit -m "feat: domain models (users, tickets, draws, results)"
```

---

### Task 5: Initial Alembic migration and app-DB upgrade

**Files:**
- Create: `backend/migrations/versions/0001_initial.py` (generated)
- Create: `backend/tests/test_migration.py`

**Interfaces:**
- Consumes: all models registered in `app.models`.
- Produces: a migration that creates the `pgcrypto` extension and all tables. `alembic upgrade head` produces a schema identical to `Base.metadata`.

- [ ] **Step 1: Autogenerate the migration**

Run (with `docker compose up -d db` running and `DATABASE_URL` pointing at the app DB):
```bash
cd backend && . .venv/bin/activate && DATABASE_URL=postgresql+psycopg://lotto:lotto@localhost:5432/lotto alembic revision --autogenerate -m "initial"
```
Expected: a new file under `migrations/versions/`.

- [ ] **Step 2: Add the pgcrypto extension to the migration**

Edit the generated migration's `upgrade()` to begin with (so `gen_random_uuid()` works):
```python
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
```
and in `downgrade()` end with:
```python
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
```

- [ ] **Step 3: Apply the migration**

Run:
```bash
cd backend && . .venv/bin/activate && DATABASE_URL=postgresql+psycopg://lotto:lotto@localhost:5432/lotto alembic upgrade head
```
Expected: `Running upgrade -> 0001, initial`.

- [ ] **Step 4: Write a test that autogenerate detects no drift — `backend/tests/test_migration.py`**

```python
import subprocess
import sys


def test_no_migration_drift():
    # After upgrade head, autogenerate should detect no changes.
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "check"],
        cwd=".", capture_output=True, text=True,
        env={"PATH": __import__("os").environ["PATH"],
             "DATABASE_URL": "postgresql+psycopg://lotto:lotto@localhost:5432/lotto"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
```

- [ ] **Step 5: Run the drift test**

Run:
```bash
cd backend && . .venv/bin/activate && pytest tests/test_migration.py -v
```
Expected: PASS (`alembic check` reports no new upgrade operations).

- [ ] **Step 6: Commit**

```bash
git add backend && git commit -m "feat: initial alembic migration"
```

---

### Task 6: Seed game and prize-rule reference data

**Files:**
- Create: `backend/app/seed.py`
- Create: `backend/tests/test_seed.py`

**Interfaces:**
- Consumes: `SessionLocal`, `Game`, `PrizeRule`.
- Produces:
  - `app.seed.seed_reference_data(session)` — idempotent (upsert by `key`/`tier_key`); inserts all 5 games with correct number ranges/prices/schedules and their fixed prize tiers (Powerball 9 tiers, Mega Millions base tiers, Lotto Texas fixed tier + Extra! adds, Texas Two Step fixed tiers 1+B/0+B and the pari-mutuel tier placeholders, Daily 4 straight/box/pairs).
  - `python -m app.seed` runnable entry point that seeds the app DB.

- [ ] **Step 1: Create `backend/app/seed.py`** — the games plus their fixed prize tiers. Amounts in cents; pari-mutuel tiers get `base_amount_cents=None` (payout comes from the scrape in Plan 4).

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.reference import Game, PrizeRule

GAMES = [
    dict(key="powerball", display_name="Powerball", main_count=5, main_min=1,
         main_max=69, has_special_ball=True, special_min=1, special_max=26,
         base_price_cents=200, prize_type="fixed",
         draw_schedule={"days": ["Mon", "Wed", "Sat"], "time": "21:59"}),
    dict(key="mega_millions", display_name="Mega Millions", main_count=5, main_min=1,
         main_max=70, has_special_ball=True, special_min=1, special_max=24,
         base_price_cents=500, prize_type="fixed",
         draw_schedule={"days": ["Tue", "Fri"], "time": "21:59"}),
    dict(key="lotto_texas", display_name="Lotto Texas", main_count=6, main_min=1,
         main_max=54, has_special_ball=False, base_price_cents=100,
         prize_type="pari_mutuel",
         draw_schedule={"days": ["Mon", "Wed", "Sat"], "time": "22:12"}),
    dict(key="texas_two_step", display_name="Texas Two Step", main_count=4, main_min=1,
         main_max=35, has_special_ball=True, special_min=1, special_max=35,
         base_price_cents=100, prize_type="mixed",
         draw_schedule={"days": ["Mon", "Thu"], "time": "22:12"}),
    dict(key="daily4", display_name="Daily 4", main_count=4, main_min=0, main_max=9,
         has_special_ball=False, base_price_cents=100, prize_type="fixed",
         draw_schedule={"days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                        "periods": {"morning": "10:00", "day": "12:27",
                                     "evening": "18:00", "night": "22:12"}}),
]

# tier_key, match_main, match_special, play_type, base_amount_cents
# Amounts are $1-wager base amounts in cents. pari-mutuel tiers -> None.
PRIZE_RULES = {
    "powerball": [
        ("5+PB", 5, True, None, None),        # jackpot
        ("5", 5, False, None, 100_000_000),
        ("4+PB", 4, True, None, 5_000_000),
        ("4", 4, False, None, 10_000),
        ("3+PB", 3, True, None, 10_000),
        ("3", 3, False, None, 700),
        ("2+PB", 2, True, None, 700),
        ("1+PB", 1, True, None, 400),
        ("0+PB", 0, True, None, 400),
    ],
    "mega_millions": [
        ("5+MB", 5, True, None, None),         # jackpot
        ("5", 5, False, None, 100_000_000),
        ("4+MB", 4, True, None, 1_000_000),
        ("4", 4, False, None, 50_000),
        ("3+MB", 3, True, None, 20_000),
        ("3", 3, False, None, 1_000),
        ("2+MB", 2, True, None, 1_000),
        ("1+MB", 1, True, None, 400),
        ("0+MB", 0, True, None, 200),
    ],
    "lotto_texas": [
        ("6", 6, False, None, None),           # jackpot, pari-mutuel
        ("5", 5, False, None, None),           # pari-mutuel
        ("4", 4, False, None, None),           # pari-mutuel
        ("3", 3, False, None, 300),            # fixed $3
    ],
    "texas_two_step": [
        ("4+B", 4, True, None, None),          # jackpot, pari-mutuel
        ("4", 4, False, None, None),           # pari-mutuel (~$1,501)
        ("3+B", 3, True, None, None),          # pari-mutuel (~$50)
        ("3", 3, False, None, None),           # pari-mutuel (~$20)
        ("2+B", 2, True, None, None),          # pari-mutuel (~$20)
        ("1+B", 1, True, None, 700),           # fixed $7
        ("0+B", 0, True, None, 500),           # fixed $5
    ],
    # Daily 4 base ($1 wager) fixed amounts; Fireball handled in prize engine (Plan 3).
    "daily4": [
        ("straight", 4, False, "straight", 500_000),
        ("box-4", 4, False, "box-4", 120_000),
        ("box-6", 4, False, "box-6", 80_000),
        ("box-12", 4, False, "box-12", 40_000),
        ("box-24", 4, False, "box-24", 20_000),
        ("pair-front", 2, False, "pair-front", 5_000),
        ("pair-mid", 2, False, "pair-mid", 5_000),
        ("pair-back", 2, False, "pair-back", 5_000),
    ],
}


def seed_reference_data(session: Session) -> None:
    for g in GAMES:
        existing = session.scalar(select(Game).where(Game.key == g["key"]))
        if existing:
            for k, v in g.items():
                setattr(existing, k, v)
            game = existing
        else:
            game = Game(**g)
            session.add(game)
        session.flush()
        for tier_key, mm, ms, pt, amt in PRIZE_RULES[g["key"]]:
            rule = session.scalar(
                select(PrizeRule).where(
                    PrizeRule.game_id == game.id,
                    PrizeRule.tier_key == tier_key,
                    PrizeRule.play_type.is_(pt) if pt is None else PrizeRule.play_type == pt,
                )
            )
            if rule is None:
                rule = PrizeRule(game_id=game.id, tier_key=tier_key)
                session.add(rule)
            rule.match_main = mm
            rule.match_special = ms
            rule.play_type = pt
            rule.base_amount_cents = amt
    session.commit()


if __name__ == "__main__":
    with SessionLocal() as s:
        seed_reference_data(s)
        print("Seeded reference data.")
```

- [ ] **Step 2: Write the failing test — `backend/tests/test_seed.py`**

```python
from sqlalchemy import select

from app.models.reference import Game, PrizeRule
from app.seed import seed_reference_data


def test_seed_creates_five_games(db_session):
    seed_reference_data(db_session)
    keys = set(db_session.scalars(select(Game.key)).all())
    assert keys == {"powerball", "mega_millions", "lotto_texas",
                    "texas_two_step", "daily4"}


def test_seed_powerball_rules_and_ranges(db_session):
    seed_reference_data(db_session)
    pb = db_session.scalar(select(Game).where(Game.key == "powerball"))
    assert (pb.main_max, pb.special_max, pb.base_price_cents) == (69, 26, 200)
    match5 = db_session.scalar(
        select(PrizeRule).where(PrizeRule.game_id == pb.id, PrizeRule.tier_key == "5"))
    assert match5.base_amount_cents == 100_000_000  # $1,000,000


def test_seed_is_idempotent(db_session):
    seed_reference_data(db_session)
    seed_reference_data(db_session)
    assert len(db_session.scalars(select(Game)).all()) == 5
```

Note: `seed_reference_data` calls `session.commit()`; within the rolled-back test transaction this commits to the savepoint/connection and is undone by the fixture's outer rollback — tests remain isolated.

- [ ] **Step 3: Run the tests to verify they pass**

Run:
```bash
cd backend && . .venv/bin/activate && pytest tests/test_seed.py -v
```
Expected: PASS (3 tests).

- [ ] **Step 4: Seed the running app DB and verify**

Run:
```bash
cd backend && . .venv/bin/activate && DATABASE_URL=postgresql+psycopg://lotto:lotto@localhost:5432/lotto python -m app.seed
```
Expected: `Seeded reference data.`

- [ ] **Step 5: Run the full backend test suite**

Run:
```bash
cd backend && . .venv/bin/activate && pytest -v
```
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend && git commit -m "feat: seed games + prize rules reference data"
```

---

## Self-Review Notes

- **Spec coverage (this plan):** §2 architecture (Docker/Postgres/FastAPI) → Tasks 1–2; §3 full data model → Tasks 3–5; seeded reference data + §8 game rules → Task 6; CORS-allow-all dev requirement → Task 1. Auth logic, tickets/prize engine, pipeline, OCR, analytics, and frontend are **out of scope for this plan** and covered by Plans 2–7.
- **Deferred/verify-on-execution:** the exact Mega Millions base tier amounts and Daily 4 box amounts in Task 6 are the standard published values; verify against the source PDFs when the prize engine (Plan 3) is built. Pari-mutuel tiers intentionally carry `base_amount_cents=None`.
- **No placeholders:** every code step contains complete, runnable code.
