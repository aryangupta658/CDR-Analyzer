from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "cdr_analyzer.db"


NEW_COLUMNS: dict[str, str] = {
    "pan_no": "VARCHAR(100)",
    "target_number": "VARCHAR(50)",
    "call_type": "VARCHAR(30)",
    "connection_type": "VARCHAR(50)",
    "b_party_number": "VARCHAR(50)",
    "lrn_number": "VARCHAR(100)",
    "lrn_translation": "VARCHAR(255)",
    "call_date_raw": "VARCHAR(50)",
    "call_time_raw": "VARCHAR(100)",
    "first_bts_location": "TEXT",
    "first_cell_global_id": "VARCHAR(255)",
    "first_latitude": "FLOAT",
    "first_longitude": "FLOAT",
    "last_bts_location": "TEXT",
    "last_cell_global_id": "VARCHAR(255)",
    "last_latitude": "FLOAT",
    "last_longitude": "FLOAT",
    "sms_centre_number": "VARCHAR(100)",
    "service_type": "VARCHAR(50)",
    "imei_esn": "VARCHAR(50)",
    "imsi_min": "VARCHAR(50)",
    "call_forwarding_number": "VARCHAR(100)",
    "roaming_network_circle": "VARCHAR(255)",
    "switch_msc_id": "VARCHAR(100)",
    "in_tg": "VARCHAR(100)",
    "out_tg": "VARCHAR(100)",
}

INDEXES: dict[str, str] = {
    "ix_cdr_records_pan_no": "pan_no",
    "ix_cdr_records_target_number": "target_number",
    "ix_cdr_records_b_party_number": "b_party_number",
    "ix_cdr_records_first_cell_global_id": "first_cell_global_id",
    "ix_cdr_records_last_cell_global_id": "last_cell_global_id",
}


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def existing_columns(connection: sqlite3.Connection) -> set[str]:
    return {str(row[1]) for row in connection.execute('PRAGMA table_info("cdr_records")')}


def existing_indexes(connection: sqlite3.Connection) -> set[str]:
    return {str(row[1]) for row in connection.execute('PRAGMA index_list("cdr_records")')}


def main() -> None:
    print("=" * 68)
    print("CDR Analyzer 23-field database migration")
    print("=" * 68)
    print(f"Database: {DATABASE_PATH}")

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            "cdr_analyzer.db was not found. Start the backend once, then run this script again."
        )

    connection = sqlite3.connect(DATABASE_PATH)
    try:
        if not table_exists(connection, "cdr_records"):
            raise RuntimeError("The cdr_records table does not exist. Start FastAPI once first.")

        columns = existing_columns(connection)
        added_columns = 0
        for column_name, column_type in NEW_COLUMNS.items():
            if column_name in columns:
                print(f"[EXISTS] {column_name}")
                continue
            connection.execute(
                f'ALTER TABLE "cdr_records" ADD COLUMN "{column_name}" {column_type}'
            )
            print(f"[ADDED]  {column_name}")
            added_columns += 1

        columns = existing_columns(connection)
        indexes = existing_indexes(connection)
        added_indexes = 0
        for index_name, column_name in INDEXES.items():
            if column_name not in columns or index_name in indexes:
                continue
            connection.execute(
                f'CREATE INDEX "{index_name}" ON "cdr_records" ("{column_name}")'
            )
            print(f"[INDEX]  {index_name}")
            added_indexes += 1

        connection.commit()

        missing = sorted(set(NEW_COLUMNS) - existing_columns(connection))
        if missing:
            raise RuntimeError(f"Migration incomplete. Missing columns: {', '.join(missing)}")

        print("=" * 68)
        print(f"Migration completed. Columns added: {added_columns}; indexes added: {added_indexes}")
        print("=" * 68)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
