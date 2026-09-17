"""Docker'siz mahalliy ishlash uchun: pgserver orqali haqiqiy Postgres binary'sini
ishga tushiradi (pip orqali yuklab olinadi, tizimga o'rnatilmaydi).

Faqat DEV muhiti uchun. Production'da docker-compose.yml dagi haqiqiy
`postgres` servisidan foydalaniladi.

Ishlatish:
    uv run python scripts/dev_postgres.py
"""

import pathlib
import sys

import pgserver

PGDATA = pathlib.Path(__file__).parent.parent / ".devdata" / "pgdata"
DB_NAME = "uniassist"
DB_USER = "uniassist"
DB_PASSWORD = "change-me"


def main() -> None:
    PGDATA.parent.mkdir(parents=True, exist_ok=True)
    first_run = not PGDATA.exists()

    server = pgserver.get_server(PGDATA, cleanup_mode=None)
    print(f"Postgres ishga tushdi: {server.get_uri()}")

    if first_run:
        server.psql(f"CREATE USER {DB_USER} WITH PASSWORD '{DB_PASSWORD}' SUPERUSER;")
        server.psql(f"CREATE DATABASE {DB_NAME} OWNER {DB_USER};")
        print(f"'{DB_NAME}' bazasi va '{DB_USER}' foydalanuvchisi yaratildi.")

    print(
        "\n.env faylida quyidagilar bo'lishi kerak:\n"
        f"  POSTGRES_HOST=localhost\n"
        f"  POSTGRES_PORT={server.get_uri().split(':')[-1].split('/')[0]}\n"
        f"  POSTGRES_USER={DB_USER}\n"
        f"  POSTGRES_PASSWORD={DB_PASSWORD}\n"
        f"  POSTGRES_DB={DB_NAME}\n"
    )
    print("Server fonda ishlayveradi (cleanup_mode=None) — bu skriptni yopsangiz ham to'xtamaydi.")
    print("To'xtatish uchun: uv run python scripts/dev_postgres_stop.py")


if __name__ == "__main__":
    sys.exit(main())
