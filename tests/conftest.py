from __future__ import annotations

import pytest
import aiosqlite

from app.db import init_db
from app.tickets.storage import TicketStorage


@pytest.fixture
async def db_connection(tmp_path):
    connection = await aiosqlite.connect(tmp_path / "test.sqlite3")
    await init_db(connection)
    yield connection
    await connection.close()


@pytest.fixture
async def storage(db_connection):
    return TicketStorage(db_connection)