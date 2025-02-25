import os
import time
from threading import Thread
from psycopg2.pool import ThreadedConnectionPool

from bot import Bot
from main_socket import MainSocket


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


if __name__ == "__main__":
    bot = Bot("%", None)

    time.sleep(2)

    pool = ThreadedConnectionPool(1, 5, host=POSTGRES_HOST, database=POSTGRES_DB, user=POSTGRES_USER, password=POSTGRES_PASSWORD, port=POSTGRES_PORT)
    bot.set_pool(pool)

    connection = pool.getconn()
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS gge_events (id INT PRIMARY KEY, end_time INT, content TEXT, discount INT, new INT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS e4k_events (id INT PRIMARY KEY, end_time INT, content TEXT, discount INT, new INT)")
    connection.commit()
    pool.putconn(connection)

    time.sleep(2)

    gge_socket = MainSocket(pool, "wss://ep-live-fr1-game.goodgamestudios.com/", "EmpireEx_3", GGE_USERNAME, GGE_PASSWORD)
    Thread(target=gge_socket.run_forever, kwargs={'reconnect': 600}).start()

    time.sleep(2)
    
    e4k_socket = MainSocket(pool, "ws://e4k-live-int4-game.goodgamestudios.com/", "EmpirefourkingdomsExGG_34", E4K_USERNAME, E4K_PASSWORD)
    Thread(target=e4k_socket.run_forever, kwargs={'reconnect': 600}).start()

    time.sleep(2)

    bot.run(DISCORD_TOKEN)
