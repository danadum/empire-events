from threading import Thread
import os
from dotenv import load_dotenv
from firebase import firebase
from main_socket import MainSocket
from bot import Bot

load_dotenv()

NOM = os.getenv("NOM")
MDP = os.getenv("PASSWORD")

if __name__ == "__main__":
    base = firebase.FirebaseApplication("https://gge-bot-default-rtdb.europe-west1.firebasedatabase.app", None)

    socket = MainSocket("wss://ep-live-fr1-game.goodgamestudios.com/", base, NOM, MDP)
    Thread(target=socket.run_forever, kwargs={'reconnect': 600}).start()

    Bot("%", base).run(os.getenv("TOKEN"))
