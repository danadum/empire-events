import logging
import time
import discord
from discord.ext import commands, tasks
import requests
import ijson

class Bot(commands.Bot):
    def __init__(self, prefix, pool):
        with requests.get("https://empire-html5.goodgamestudios.com/default/items/ItemsVersion.properties") as response:
            items_version = response.text.split("=")[1]
        with requests.get(f"https://empire-html5.goodgamestudios.com/default/items/items_v{items_version}.json", stream=True) as response:
            response.raw.decode_content = True
            self.items = { key: value for key, value in ijson.kvitems(response.raw, '') if key in ["buildings", "shoppingCarts", "rewards"] }
        super().__init__(prefix, intents=discord.Intents.all())
        self.pool = pool
        self.channel_gge_fr = 774929943540006952
        self.channel_gge_en = 956915826894708766
        self.channel_e4k_fr = 956916103869792266
        self.channel_e4k_en = 956915929982328892

        @self.event
        async def on_ready():
            logging.error(f"### Bot running ###")
            self.main_loop.start()
    
    def set_pool(self, pool):
        self.pool = pool

    @tasks.loop(seconds=300)
    async def main_loop(self):
        if not self.send_event_notifications.is_running():
            self.send_event_notifications.start()

    @tasks.loop(seconds=60)
    async def send_event_notifications(self):
        for game in ["gge", "e4k"]:
            connection = self.pool.getconn()
            cursor = connection.cursor()
            cursor.execute(f"SELECT * FROM {game}_events WHERE new = 1")
            new_events = cursor.fetchall()
            self.pool.putconn(connection)
            for event in new_events:
                if event[1] > int(time.time()):
                    names = self.get_event_names(event)
                    if names is not None:
                        if event[3] != 0:
                            names = f"{names[0]} Réduction de {event[3]}%", f"{names[1]} Discount of {event[3]}%"
                            if event[0] == 7:
                                building = next(filter(lambda obj: str(obj["wodID"]) == event[2], self.items["buildings"]))
                                cost = int(int(building["costC2"]) * (1 - (event[3] / 100)))
                                names = f"{names[0]} (le nouveau coût est de {cost} rubis)", f"{names[1]} (the new cost is {cost} rubies)"
                        if game == "gge":
                            messages = [
                                await self.get_channel(self.channel_gge_fr).send(f"{names[0]}, fin à <t:{event[1]}:t> (<t:{event[1]}:R>)"),
                                await self.get_channel(self.channel_gge_en).send(f"{names[1]}, ends at <t:{event[1]}:t> (<t:{event[1]}:R>)")
                            ]
                        else:
                            messages = [
                                await self.get_channel(self.channel_e4k_fr).send(f"{names[0]}, fin à <t:{event[1]}:t> (<t:{event[1]}:R>)"),
                                await self.get_channel(self.channel_e4k_en).send(f"{names[1]}, ends at <t:{event[1]}:t> (<t:{event[1]}:R>)")
                            ]
                        
                        for message in messages:
                            try:
                                await message.publish()
                            except Exception as e:
                                logging.error(f""""Failed to publish message: {e}""")

                        connection = self.pool.getconn()
                        cursor = connection.cursor()
                        cursor.execute(f"UPDATE {game}_events SET new = 0 WHERE id = {event[0]}")
                        connection.commit()
                        self.pool.putconn(connection)

    def get_event_names(self, event):
        if event[0] == 7:
            if event[2] == "798":  # boulangerie 1
                return "<@&799265497342410752>", "<@&961545877867094016>"
            elif event[2] == "124":
                return "<@&799266002318786601>", "<@&961545933265440869>"
            elif event[2] == "799":
                return "<@&799266046099324938>", "<@&961545937614946354>"
            elif event[2] == "125":
                return "<@&799266093331644446>", "<@&961545951317749800>"
            elif event[2] == "800":
                return "<@&799266137887866942>", "<@&961545958146072596>"
            elif event[2] == "126":
                return "<@&799266183081099304>", "<@&961545961757376533>"
            elif event[2] == "801":
                return "<@&799266228623507458>", "<@&961545964508835861>"
            elif event[2] == "196":  # boulangerie 8
                return "<@&799266269916430336>", "<@&961545966224293918>"
            elif event[2] == "4":  # hôpital 4
                return "<@&799266642487935007>", "<@&961558348078120990>"
            elif event[2] == "463":
                return "<@&799266927515009025>", "<@&961558365232828446>"
            elif event[2] == "464":
                return "<@&799266972410970122>", "<@&961558380701437962>"
            elif event[2] == "465":
                return "<@&799267046574915644>", "<@&961558393447919627>"
            elif event[2] == "466":
                return "<@&799267103332368416>", "<@&961558407972786206>"
            elif event[2] == "467":
                return "<@&799267147519229952>", "<@&961558421210026035>"
            elif event[2] == "5":  # hôpital 10
                return "<@&799267202557280276>", "<@&961558437534249000>"
            elif event[2] == "215":  # écuries 2
                return "<@&799266481551441950>", "<@&961557929557917746>"
            elif event[2] == "226":  # écuries 3
                return "<@&799266534077890610>", "<@&961557999078490122>"
            elif event[2] == "456":  # douves 1
                return "<@&799267381925904395>", "<@&961558836974587914>"
            elif event[2] == "831":  # douves 2
                return "<@&799267437681442827>", "<@&961558870579380224>"
        elif event[0] == 75:
            if event[2] == "[2]":  # contremaître pain
                return "<@&961603178787373086>", "<@&961623169486159872>"
            elif event[2] == "[6]":  # maraudeur
                return "<@&961603183719882832>", "<@&961623119066431488>"
            elif event[2] == "[10]":  # sergent instructeur
                return "<@&961603187272458252>", "<@&961625064304959489>"
        elif event[0] == 90:
            cart = event[2].strip("[]").replace(" ", "").split(",")
            cart = [cart[0:6], cart[6:12], cart[12:18]]
            nb_skips = 0
            for side in cart:
                for option_type in side:
                    option = next(filter(lambda obj: (obj["typeID"] == option_type), self.items["shoppingCarts"]))
                    reward = next(filter(lambda obj: (obj["rewardID"] == option["rewardID"]), self.items["rewards"]))
                    if reward.get("add60MinSkip") or reward.get("add30MinSkip"):
                        nb_skips += 1
                        break
            if nb_skips == 3:
                return "<@&1073618582254125126>", "<@&1073619021783634000>"
        elif event[0] == 999 and int(event[2]) >= 200:  # 200% vert
            return f"<@&772138513323917382> Promo de {event[2]}%", f"<@&772138513323917382> Prime time of {event[2]}%"
        elif event[0] == 998 and int(event[2]) >= 200:  # 200% RE
            return f"<@&841978302562172969> Promo de {event[2]}%", f"<@&841978302562172969> Prime time of {event[2]}%"
        elif event[0] == 997 and int(event[2]) >= 200:  # 200% Lacis
            return f"<@&841978439329644606> Promo de {event[2]}%", f"<@&841978439329644606> Prime time of {event[2]}%"
