import os
import time
from threading import Thread

from lib.database import Database
from lib.bot import Bot
from lib.main_socket import MainSocket


GGE_USERNAME = os.getenv("GGE_USERNAME")
GGE_PASSWORD = os.getenv("GGE_PASSWORD")

E4K_USERNAME = os.getenv("E4K_USERNAME")
E4K_PASSWORD = os.getenv("E4K_PASSWORD")

POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")


DISCORD_PREFIX = "%"

DB_POOL_MINCONN = 1
DB_POOL_MAXCONN = 5

GGE_SERVER = "wss://ep-live-fr1-game.goodgamestudios.com/"
GGE_SERVER_HEADER = "EmpireEx_3"

E4K_SERVER = "ws://e4k-live-int4-game.goodgamestudios.com/"
E4K_SERVER_HEADER = "EmpirefourkingdomsExGG_34"


if __name__ == "__main__":
    bot = Bot(DISCORD_PREFIX, None)

    time.sleep(2)

    database = Database(minconn=DB_POOL_MINCONN, maxconn=DB_POOL_MAXCONN, host=POSTGRES_HOST, database=POSTGRES_DB, user=POSTGRES_USER, password=POSTGRES_PASSWORD, port=POSTGRES_PORT)
    bot.set_database(database)

    database.execute("CREATE TABLE IF NOT EXISTS gge_events (id INT PRIMARY KEY, end_time INT, content TEXT, discount INT, new INT)")
    database.execute("CREATE TABLE IF NOT EXISTS e4k_events (id INT PRIMARY KEY, end_time INT, content TEXT, discount INT, new INT)")

    time.sleep(2)

    gge_socket = MainSocket(database, GGE_SERVER, GGE_SERVER_HEADER, GGE_USERNAME, GGE_PASSWORD)
    Thread(target=gge_socket.run_forever, kwargs={'reconnect': 600}).start()
    bot.set_gge_socket(gge_socket)

    time.sleep(2)
    
    e4k_socket = MainSocket(database, E4K_SERVER, E4K_SERVER_HEADER, E4K_USERNAME, E4K_PASSWORD)
    Thread(target=e4k_socket.run_forever, kwargs={'reconnect': 600}).start()
    bot.set_e4k_socket(e4k_socket)

    time.sleep(2)

    bot.run(DISCORD_TOKEN)
