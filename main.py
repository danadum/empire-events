from threading import Thread
import os
from dotenv import load_dotenv
from firebase import firebase
from main_socket import MainSocket
from main_socket_e4k import MainSocketE4K
from bot import Bot

load_dotenv()

NOM = os.getenv("NOM")
MDP = os.getenv("PASSWORD")

NOM_E4K = os.getenv("NOM_E4K")
MDP_E4K = os.getenv("PASSWORD_E4K")

if __name__ == "__main__":
    base = firebase.FirebaseApplication("https://gge-bot-default-rtdb.europe-west1.firebasedatabase.app", None)

    socket = MainSocket("wss://ep-live-fr1-game.goodgamestudios.com/", base, NOM, MDP)
    Thread(target=socket.run_forever, kwargs={'reconnect': 600}).start()

    socket_e4k = MainSocketE4K("ws://e4k-live-int4-game.goodgamestudios.com/", base, NOM_E4K, MDP_E4K)
    Thread(target=socket_e4k.run_forever, kwargs={'reconnect': 600}).start()

    Bot("%", base).run(os.getenv("TOKEN"))
