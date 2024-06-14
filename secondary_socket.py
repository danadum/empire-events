import logging
from datetime import datetime
from threading import Thread
import time
import websocket
import json


class SecondarySocket(websocket.WebSocketApp):
    def __init__(self, url, base, header, token, type_serveur, main_socket, folder):
        super().__init__(url, on_open=self.on_open, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)
        self.base = base
        self.header = header
        self.token = token
        self.type_serveur = type_serveur
        self.main_socket = main_socket
        self.folder = folder

    def on_open(self, ws):
        logging.error(f"### [{datetime.now()}] Secondary socket connected ###")
        Thread(target=self.run).start()

    def run(self):
        self.send("""<msg t='sys'><body action='verChk' r='0'><ver v='166' /></body></msg>""")
        self.send("""<msg t='sys'><body action='autoJoin' r='-1'></body></msg>""")
        self.send(f"""<msg t='sys'><body action='login' r='0'><login z='{self.header}'><nick><![CDATA[]]></nick><pword><![CDATA[1065004%fr%0]]></pword></login></body></msg>""")
        self.send("""<msg t='sys'><body action='roundTrip' r='1'></body></msg>""")
        self.send(f"""%xt%{self.header}%tle%1%{{"TLT":"{self.token}"}}%""")
        time.sleep(1)
        while self.sock is not None:
            self.send(f"""%xt%{self.header}%pin%1%<RoundHouseKick>%""")
            time.sleep(60)

    def on_message(self, ws, message):
        message = message.decode('UTF-8')
        if message[:17] == "%xt%core_poe%1%0%":
            data = json.loads(message[17:-1])
            if data["remainingTime"] > 30 and int(data["type"]) == 1:
                temps = data["remainingTime"] + int(time.time())
                identifier = 998 if self.type_serveur == "RE" else 997
                old_event = self.base.get(f"{self.folder}/{identifier}", None)
                if old_event["temps"] < int(time.time()) or old_event["contenu"] != data["bonusPremium"]:
                    self.base.patch(f"{self.folder}/{identifier}", {"temps": temps, "contenu": data["bonusPremium"], "reduction": 0, "nouveau": 1})

    def on_error(self, ws, error):
        logging.error("### error in secondary socket ###")
        logging.error(error)
        self.close()

    def on_close(self, ws, close_status_code, close_msg):
        logging.error(f"### [{datetime.now()}] Secondary socket closed ###")
        self.main_socket.temp_serveur = None
