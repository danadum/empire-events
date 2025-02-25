import math
import logging
from threading import Thread
import time
import traceback

from pygge.gge_socket import GgeSocket
from secondary_socket import SecondarySocket


class MainSocket(GgeSocket):
    def __init__(self, connection, cursor, url, server_header, username, password):
        super().__init__(url, server_header, on_open=self.on_open, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)
        self.game = "GGE" if server_header.startswith("EmpireEx") else "E4K"
        self.connection = connection
        self.cursor = cursor
        self.username = username
        self.password = password
        self.temp_socket = None

    def on_open(self, ws):
        logging.error(f"### Main socket {self.game} connected ###")
        Thread(target=self.run).start()

    def run(self):
        self.init_socket()
        Thread(target=self.keep_alive).start()
        if self.game == "GGE":
            self.login(self.username, self.password)
        else:
            self.login_e4k(self.username, self.password)
        Thread(target=self.offerings_thread).start()
        Thread(target=self.attacks_thread).start()
        Thread(target=self.events_thread).start()

    def offerings_thread(self):
        while self.sock is not None:
            offerings_response = self.get_offerings_status()
            if offerings_response["payload"]["status"] == 0:
                if offerings_response["payload"]["data"]["CHR"][0]["FOA"] > 0:
                    self.make_offering(1, 6001)
                elif offerings_response["payload"]["data"]["CHR"][1]["FOA"] > 0:
                    self.make_offering(2, 6002)
                elif offerings_response["payload"]["data"]["CHR"][2]["FOA"] > 0:
                    self.make_offering(3, 6003)
            time.sleep(3600)

    def attacks_thread(self):
        while self.sock is not None:
            castles_response = self.get_castles()
            great_empire = next(filter(lambda kingdom: kingdom["KID"] == 0, castles_response["payload"]["data"]["C"]))
            main_castle = next(filter(lambda castle: castle["AI"][0] == 1, great_empire["AI"]))["AI"]
            map_response = self.get_map_chunk(0, main_castle[1] // 13 * 13, main_castle[2] // 13 * 13)
            for map_object in map_response["payload"]["data"]["AI"]:
                if len(map_object) == 7 and map_object[0] == 2 and map_object[5] < 0:
                    movements_response = self.get_movements()
                    movements = [movement for movement in movements_response["payload"]["data"]["M"] if movement["M"]["OID"] == main_castle[4] and movement.get("UM") is not None]
                    used_lords = [movement["UM"]["L"].get("ID") for movement in movements]
                    current_attacks = [movement["M"]["TA"] for movement in movements if len(movement["M"]["TA"]) == 7 and movement["M"]["TA"][0] == 2]
                    if next(filter(lambda attack_target: attack_target[1] == map_object[1] and attack_target[2] == map_object[2], current_attacks), None) is None:
                        target_response = self.get_target_infos(0, main_castle[1], main_castle[2], map_object[1], map_object[2])
                        lord = next(filter(lambda com: com["ID"] not in used_lords, target_response["payload"]["data"]["gli"]["C"]), None)
                        unit_type = None
                        if next(filter(lambda obj: obj[0] == 9, target_response["payload"]["data"]["gui"]["I"]), [0, 0])[1] > 320:
                            unit_type = 9
                        elif next(filter(lambda obj: obj[0] == 10, target_response["payload"]["data"]["gui"]["I"]), [0, 0])[1] > 320:
                            unit_type = 10
                        if lord is not None and unit_type is not None:
                            level = math.floor(1.9 * map_object[4] ** 0.555) + 1
                            max_units = min(260, 5 * level + 8) if level <= 69 else 320
                            flank_limit = math.ceil(0.2 * max_units)
                            front_limit = max_units - 2 * flank_limit
                            waves = [{"L": {"T": [], "U": [unit_type, flank_limit]}, "R": {"T": [], "U": [unit_type, flank_limit]}, "M": {"T": [], "U": []}}]
                            final_wave = [[unit_type, 100 + level]]
                            self.send_attack(0, main_castle[1], main_castle[2], map_object[1], map_object[2], waves, lord["ID"], horses_type=1007, final_wave=final_wave)
                            logging.error(f"""GGE attacking NPC at position {map_object[1]}:{map_object[2]}""")
                            time.sleep(5)
            time.sleep(600)

    def events_thread(self):
        while self.sock is not None:
            events_response = self.get_events()
            for event in events_response["payload"]["data"]["E"]:
                if event["RS"] > 30 and event["EID"] in [7, 75, 90]:
                    end_time = int(event['RS']) + int(time.time())
                    content = str(event.get("WID") or event.get("BID") or event.get("TID"))
                    discount = event.get('DIS', 0)
                    self.cursor.execute(f"SELECT * FROM {self.game.lower()}_events WHERE id = {event['EID']}")
                    old_event = self.cursor.fetchone()
                    if old_event is None:
                        self.cursor.execute(f"INSERT INTO {self.game.lower()}_events (id, end_time, content, discount, new) VALUES ({event['EID']}, {end_time}, '{content}', {discount}, 1)")
                        self.connection.commit()
                    elif old_event[1] < int(time.time()) or old_event[2] != content or old_event[3] != discount:
                        self.cursor.execute(f"UPDATE {self.game.lower()}_events SET end_time = {end_time}, content = '{content}', discount = {discount}, new = 1 WHERE id = {event['EID']}")
                        self.connection.commit()
                elif event["EID"] == 106 and (self.temp_socket is None or self.temp_socket.sock is None):
                    if event["IPS"] == 0:
                        if event["TSID"] in [16, 18]:
                            self.buy_package_generic(0, 0, 106, 2358, 1)
                            self.choose_outer_realm_castle(40)
                        else:
                            self.choose_outer_realm_castle(31, only_rubies=1)
                    token_response = self.get_outer_realm_token()
                    if token_response["payload"]["data"]['TSIP'].startswith('e4k'):
                        temp_socket_url = f"ws://{token_response['payload']['data']['TSIP']}"
                    else:
                        temp_socket_url = f"wss://{token_response['payload']['data']['TSIP']}"
                    self.temp_socket = SecondarySocket(self.connection, self.cursor, self.game, temp_socket_url, token_response["payload"]["data"]["TSZ"], token_response["payload"]["data"]["TLT"], "OR")
                    Thread(target=self.temp_socket.run_forever, kwargs={'reconnect': False}).start()
                elif event["EID"] == 113 and (self.temp_socket is None or self.temp_socket.sock is None):
                    if event["IPS"] == 0:
                        self.choose_bth_castle(34, only_rubies=1)
                    token_response = self.get_bth_token()
                    if token_response["payload"]["data"]['TSIP'].startswith('e4k'):
                        temp_socket_url = f"ws://{token_response['payload']['data']['TSIP']}"
                    else:
                        temp_socket_url = f"wss://{token_response['payload']['data']['TSIP']}"
                    self.temp_socket = SecondarySocket(self.connection, self.cursor, self.game, temp_socket_url, token_response["payload"]["data"]["TSZ"], token_response["payload"]["data"]["TLT"], "BTH")
                    Thread(target=self.temp_socket.run_forever, kwargs={'reconnect': False}).start()
                elif event["EID"] == 117 and event.get("FTDC") == 1:
                    self.make_divination()
                elif event["EID"] == 15 and event.get("OP") is not None and event.get("OP")[0] < 3:
                    self.spin_classic_lucky_wheel()
            time.sleep(60)

    def on_message(self, ws, message):
        message = self.parse_response(message)
        if message["type"] == "json" and message["payload"]["command"] == "core_poe" and message["payload"]["status"] == 0:
            if message["payload"]["data"]["remainingTime"] > 30 and message["payload"]["data"]["type"] == 1:
                end_time = message["payload"]["data"]["remainingTime"] + int(time.time())
                self.cursor.execute(f"SELECT * FROM {self.game.lower()}_events WHERE id = 999")
                old_event = self.cursor.fetchone()
                if old_event is None:
                    self.cursor.execute(f"INSERT INTO {self.game.lower()}_events (id, end_time, content, discount, new) VALUES (999, {end_time}, '{message['payload']['data']['bonusPremium']}', 0, 1)")
                    self.connection.commit()
                elif old_event[1] < int(time.time()) or old_event[2] != message["payload"]["data"]["bonusPremium"]:
                    self.cursor.execute(f"UPDATE {self.game.lower()}_events SET end_time = {end_time}, content = '{message['payload']['data']['bonusPremium']}', discount = 0, new = 1 WHERE id = 999")
                    self.connection.commit()

    def on_error(self, ws, error):
        logging.error(f"### error in main socket {self.game} ###")
        logging.error(traceback.format_exc())
        self.close()

    def on_close(self, ws, close_status_code, close_msg):
        logging.error(f"### Main socket {self.game} closed ###")
