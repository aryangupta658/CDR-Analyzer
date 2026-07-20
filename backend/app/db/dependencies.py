from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Creates one database session for one API request.

    The session is automatically closed after the request finishes.
    """

    database = SessionLocal()

    try:
        yield database
    finally:
        database.close()