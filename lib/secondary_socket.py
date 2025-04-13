import logging
from threading import Thread
import time
import traceback

from pygge.gge_socket import GgeSocket


class SecondarySocket(GgeSocket):
    def __init__(self, database, game, url, server_header, token, server_type):
        super().__init__(url, server_header, on_open=self.on_open, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)
        self.database = database
        self.game = game
        self.token = token
        self.server_type = server_type
        self.events = []

    def on_open(self, ws):
        logging.error(f"### Secondary socket {self.game} connected ###")
        Thread(target=self.run, daemon=True).start()

    def run(self):
        try:
            self.events = self.database.fetchall(f"SELECT * FROM {self.game.lower()}_events WHERE id IN (997, 998)")
            self.events = [list(event) for event in self.events]

            self.init_socket()
            Thread(target=self.keep_alive, daemon=True).start()
            if self.server_type == "OR":
                self.login_outer_realm(self.token, sync=(self.game == "GGE"))
            else:
                self.login_bth(self.token, sync=(self.game == "GGE"))
            Thread(target=self.auto_close_thread, daemon=True).start()
        except Exception as e:
            logging.error(f"error in run secondary socket {self.game}: {e}")
            logging.error(traceback.format_exc())
            self.close()

    def auto_close_thread(self):
        time.sleep(60 * 60 * 6)
        if self.sock:
            logging.warning(f"### Auto-closing Secondary socket {self.game} after 6h ###")
            self.close()

    def on_message(self, ws, message):
        try:
            message = self.parse_response(message)
            if message["type"] == "json" and message["payload"]["command"] == "core_poe" and message["payload"]["status"] == 0:
                if message["payload"]["data"]["remainingTime"] > 30 and int(message["payload"]["data"]["type"]) == 1:
                    end_time = message["payload"]["data"]["remainingTime"] + int(time.time())
                    event_id = 998 if self.server_type == "OR" else 997
                    old_event = next(filter(lambda e: e[0] == event_id, self.events), None)
                    if old_event is None:
                        self.database.execute(f"INSERT INTO {self.game.lower()}_events (id, end_time, content, discount, new) VALUES ({event_id}, {end_time}, '{message['payload']['data']['bonusPremium']}', 0, 1)")
                        self.events.append([event_id, end_time, str(message["payload"]["data"]["bonusPremium"]), 0, 1])
                    elif old_event[1] < int(time.time()) or old_event[2] != str(message["payload"]["data"]["bonusPremium"]):
                        self.database.execute(f"UPDATE {self.game.lower()}_events SET end_time = {end_time}, content = '{message['payload']['data']['bonusPremium']}', discount = 0, new = 1 WHERE id = {event_id}")
                        old_event[1:5] = [end_time, str(message["payload"]["data"]["bonusPremium"]), 0, 1]
        except Exception as e:
            logging.error(f"error in on_message secondary socket {self.game}: {e}")

    def on_error(self, ws, error):
        logging.error(f"### error in secondary socket {self.game} ###")
        logging.error(traceback.format_exc())
        self.close()

    def on_close(self, ws, close_status_code, close_msg):
        logging.error(f"### Secondary socket {self.game} closed ###")
