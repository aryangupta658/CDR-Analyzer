from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "cdr_analyzer.db"

REQUIRED_OPERATOR_COLUMNS = {
    "pan_no",
    "target_number",
    "call_type",
    "b_party_number",
    "lrn_number",
    "lrn_translation",
    "call_time_raw",
    "duration_seconds",
    "first_cell_global_id",
    "first_latitude",
    "first_longitude",
    "last_cell_global_id",
    "last_latitude",
    "last_longitude",
    "sms_centre_number",
    "service_type",
    "imei_esn",
    "imsi_min",
    "call_forwarding_number",
    "roaming_network_circle",
    "switch_msc_id",
    "in_tg",
    "out_tg",
}


def main() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DATABASE_PATH}")

    connection = sqlite3.connect(DATABASE_PATH)
    try:
        columns = {
            str(row[1]) for row in connection.execute('PRAGMA table_info("cdr_records")')
        }
        missing = sorted(REQUIRED_OPERATOR_COLUMNS - columns)

        print(f"Database: {DATABASE_PATH}")
        print(f"CDR columns present: {len(columns)}")
        if missing:
            print("Missing 23-field columns:")
            for column in missing:
                print(f"  - {column}")
            raise RuntimeError("Database schema is incomplete.")

        print("All 23 operator CDR fields are supported by the database.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
