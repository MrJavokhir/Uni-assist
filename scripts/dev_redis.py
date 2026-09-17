"""Docker'siz mahalliy ishlash uchun: fakeredis'ning haqiqiy TCP serverini
ishga tushiradi (Redis protokoliga to'liq mos, standart `redis` klient bilan ishlaydi).

Faqat DEV muhiti uchun — ma'lumot faqat xotirada, jarayon to'xtasa yo'qoladi.
Production'da docker-compose.yml dagi haqiqiy `redis` servisidan foydalaniladi.

Ishlatish:
    uv run python scripts/dev_redis.py
"""

import sys

from fakeredis import TcpFakeServer

HOST = "127.0.0.1"
PORT = 6379


def main() -> None:
    server = TcpFakeServer((HOST, PORT), server_type="redis")
    print(f"Fake Redis (dev) {HOST}:{PORT} da ishga tushdi. To'xtatish uchun Ctrl+C.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
