"""Subclass API routes backed by the vd_subclass view."""

import psycopg
from fastapi import APIRouter, Depends

from app.core.db import get_db_connection
from app.core.security import get_current_member
from app.repositories.subclass import get_subclasses_by_pcid

router = APIRouter(
    prefix="/subclass",
    tags=["subclass"],
    dependencies=[Depends(get_current_member)],
)


@router.get("/pcid/{id}")
def read_subclasses_by_pcid(
    id: int,
    connection: psycopg.Connection = Depends(get_db_connection),
) -> list[dict[str, object]]:
    """依照 parent class id 回傳所有 subclass。"""

    return get_subclasses_by_pcid(connection, id)
