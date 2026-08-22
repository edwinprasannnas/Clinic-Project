"""
PostgreSQL database layer for Willow Health Clinic bookings.

Reads connection info from the DATABASE_URL environment variable, e.g.:
    postgresql://user:password@localhost:5432/clinic

Uses a small connection pool (psycopg2) so the FastAPI app can serve
concurrent requests without opening a new TCP connection every time.

Install:
    pip install psycopg2-binary
"""
import os
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from psycopg2 import pool

# Reads a ".env" file in the project root (if present) and loads its
# variables into the environment. Safe to call even if no .env exists.
load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:EdiSumPraj@localhost:5432/willowclinic"
)

# Tune min/max connections to your expected concurrency.
_pool: pool.SimpleConnectionPool | None = None


def _get_pool() -> pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=DATABASE_URL)
    return _pool


@contextmanager
def get_db():
    p = _get_pool()
    conn = p.getconn()
    try:
        yield conn
    finally:
        p.putconn(conn)


def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS bookings (
                    id          SERIAL PRIMARY KEY,
                    name        TEXT NOT NULL,
                    phone       TEXT NOT NULL,
                    date        TEXT NOT NULL,
                    service     TEXT NOT NULL,
                    doctor      TEXT,
                    status      TEXT NOT NULL DEFAULT 'pending',
                    created_at  TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_log (
                    id          SERIAL PRIMARY KEY,
                    booking_id  INTEGER REFERENCES bookings (id),
                    event       TEXT NOT NULL,
                    detail      TEXT,
                    created_at  TEXT NOT NULL
                )
                """
            )
        conn.commit()


def _row_to_dict(cur, row) -> dict:
    colnames = [desc[0] for desc in cur.description]
    return dict(zip(colnames, row))


def create_booking(name: str, phone: str, date: str, service: str, doctor: str | None) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO bookings (name, phone, date, service, doctor, status, created_at)
                VALUES (%s, %s, %s, %s, %s, 'pending', %s)
                RETURNING id
                """,
                (name, phone, date, service, doctor, now),
            )
            booking_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO activity_log (booking_id, event, detail, created_at) VALUES (%s, %s, %s, %s)",
                (booking_id, "booking_created", f"{name} requested {service}", now),
            )
            conn.commit()
            cur.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
            row = cur.fetchone()
            return _row_to_dict(cur, row)


def list_bookings(status: str | None = None) -> list[dict]:
    with get_db() as conn:
        with conn.cursor() as cur:
            if status:
                cur.execute(
                    "SELECT * FROM bookings WHERE status = %s ORDER BY id DESC", (status,)
                )
            else:
                cur.execute("SELECT * FROM bookings ORDER BY id DESC")
            rows = cur.fetchall()
            return [_row_to_dict(cur, r) for r in rows]


def update_booking_status(booking_id: int, status: str) -> dict | None:
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE bookings SET status = %s WHERE id = %s", (status, booking_id))
            cur.execute(
                "INSERT INTO activity_log (booking_id, event, detail, created_at) VALUES (%s, %s, %s, %s)",
                (booking_id, "status_changed", status, now),
            )
            conn.commit()
            cur.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
            row = cur.fetchone()
            return _row_to_dict(cur, row) if row else None


def recent_activity(limit: int = 50) -> list[dict]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM activity_log ORDER BY id DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
            return [_row_to_dict(cur, r) for r in rows]