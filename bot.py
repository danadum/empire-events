import logging
from datetime import datetime
import time
import re
import discord
from discord.ext import commands, tasks
import json
import io
from difflib import unified_diff
import aiohttp


class Bot(commands.Bot):
    def __init__(self, prefix, base):
        super().__init__(prefix, intents=discord.Intents.all())
        self.base = base
        self.channel_fr = 774929943540006952
        self.channel_en = 956915826894708766
        self.channel_log = 1076865424295219251
        self.channel_datamine = 1069667390402592788
        self.channel_datamine2 = 1070755471679570021
        self.server_fr = 481447341849706496
        self.donnees = {}

        @self.event
        async def on_ready():
            logging.error(f"### [{datetime.now()}] Bot running ###")
            donnees_version = await getVersion("item")
            response = await getFile(f"https://empire-html5.goodgamestudios.com/default/items/items_v{donnees_version}.json")
            self.donnees = await response.json()
            self.mainLoop.start()

        @self.command(name="versions")
        async def showVersions(ctx):
            if ctx.channel.id == self.channel_datamine or ctx.guild.id != self.server_fr:
                lines = []
                for fichier in list(self.base.get("/datamine", None).items()):
                    version = await getVersion(fichier[0])
                    lines.append(f"Version actuelle {fichier[1]['nom']} : [{version}](<{fichier[1]['lien'].format(version=version)}>)")
                await ctx.send("\n".join(lines))

    @tasks.loop(seconds=300)
    async def mainLoop(self):
        if not self.show_events.is_running():
            self.show_events.start()
        if not self.checkVersions.is_running():
            self.checkVersions.start()

    @tasks.loop(seconds=60)
    async def checkVersions(self):
        now = int(time.time())
        for fichier in list(self.base.get("/datamine", None).items()):
            version_old = fichier[1]["version"]
            version = await getVersion(fichier[0])
            if version != version_old:
                old = await getFile(fichier[1]['lien'].format(version=version_old))
                new = await getFile(fichier[1]['lien'].format(version=version))
                if fichier[0].startswith("dll"):
                    old = (await old.text()).split("ItemVersions.prototype.fill=function(){", 1)[1].split("}", 1)[0].replace(';', ',').split(',')
                    old = [f"    {line}" for line in old]
                    new = (await new.text()).split("ItemVersions.prototype.fill=function(){", 1)[1].split("}", 1)[0].replace(';', ',').split(',')
                    new = [f"    {line}" for line in new]
                    comp = '\n'.join([*unified_diff(old, new, n=0)])
                    server = 'default' if fichier[0] == 'dll' else 'openBeta'
                    comp = re.sub(r"this\.assets\.([^=]*)=\"(.*)\"", lambda x: f"{x.group(1)} = https://empire-html5.goodgamestudios.com/{server}/assets/{x.group(2)}.webp", comp)
                    for line in comp.split('\n'):
                        if line.startswith('+    ') or line.startswith('-    '):
                            action = "ajoutée" if line.startswith("+") else "supprimée"
                            name = line.split("    ", 1)[1].split(" = ", 1)[0]
                            url = line.split(" = ", 1)[1]
                            message = f"Image {action} à <t:{now}:T> le <t:{now}:D> dans la version {version} {fichier[1]['nom']} :\n[{name}](<{url}>)"
                            async with aiohttp.ClientSession() as session:
                                async with session.get(url) as response:
                                    image = await response.read()
                                    with io.BytesIO(image) as file:
                                        await self.get_channel(self.channel_datamine2).send(message, file=discord.File(file, url.split("/")[-1]))
                else:
                    old = json.dumps(await old.json(), indent=4, ensure_ascii=False).split('\n')
                    new = json.dumps(await new.json(), indent=4, ensure_ascii=False).split('\n')
                    comp = '\n'.join([*unified_diff(old, new, n=0)])
                await self.get_channel(self.channel_datamine).send(
                    f"La version {fichier[1]['nom']} a changé à <t:{now}:T> le <t:{now}:D> !\n"
                    f"L'ancienne version était : [{version_old}](<{fichier[1]['lien'].format(version=version_old)}>)\n"
                    f"La nouvelle version est : [{version}](<{fichier[1]['lien'].format(version=version)}>)",
                    file=discord.File(fp=io.BytesIO(bytes(comp, 'utf-8')), filename="changements.txt"))
                self.base.patch(f"/datamine/{fichier[0]}", {"version": version})

    @tasks.loop(seconds=10)
    async def show_events(self):
        now = int(time.time())
        new_events = [obj for obj in self.base.get("/events", None).items() if obj[1]["nouveau"] == 1]
        await self.get_channel(self.channel_log).send(f"<t:{now}:t> {now} :\n{new_events}")
        for event in new_events:
            if event[1]["temps"] > now:
                noms = self.get_nom_event(event)
                if noms is not None:
                    if event[1]["reduction"] != 0:
                        noms = f"{noms[0]} Réduction de {event[1]['reduction']}%", f"{noms[1]} Discount of {event[1]['reduction']}%"
                        if event[0] == "7":
                            building = next(filter(lambda obj: str(obj["wodID"]) == event[1]["contenu"], self.donnees["buildings"]))
                            cout = int(int(building["costC2"]) * (1 - (event[1]["reduction"] / 100)))
                            noms = f"{noms[0]} (le nouveau coût est de {cout} rubis)", f"{noms[1]} (the new cost is {cout} rubies)"
                    await self.get_channel(self.channel_fr).send(f"{noms[0]}, fin à <t:{event[1]['temps']}:t> (<t:{event[1]['temps']}:R>)")
                    await self.get_channel(self.channel_en).send(f"{noms[1]}, ends at <t:{event[1]['temps']}:t> (<t:{event[1]['temps']}:R>)")
                    self.base.patch(f"/events/{event[0]}", {"nouveau": 0})

    def get_nom_event(self, event):
        if event[0] == "7":
            if event[1]["contenu"] == "798":  # boulangerie 1
                return "<@&799265497342410752>", "<@&961545877867094016>"
            elif event[1]["contenu"] == "124":
                return "<@&799266002318786601>", "<@&961545933265440869>"
            elif event[1]["contenu"] == "799":
                return "<@&799266046099324938>", "<@&961545937614946354>"
            elif event[1]["contenu"] == "125":
                return "<@&799266093331644446>", "<@&961545951317749800>"
            elif event[1]["contenu"] == "800":
                return "<@&799266137887866942>", "<@&961545958146072596>"
            elif event[1]["contenu"] == "126":
                return "<@&799266183081099304>", "<@&961545961757376533>"
            elif event[1]["contenu"] == "801":
                return "<@&799266228623507458>", "<@&961545964508835861>"
            elif event[1]["contenu"] == "196":  # boulangerie 8
                return "<@&799266269916430336>", "<@&961545966224293918>"
            elif event[1]["contenu"] == "4":  # hôpital 4
                return "<@&799266642487935007>", "<@&961558348078120990>"
            elif event[1]["contenu"] == "463":
                return "<@&799266927515009025>", "<@&961558365232828446>"
            elif event[1]["contenu"] == "464":
                return "<@&799266972410970122>", "<@&961558380701437962>"
            elif event[1]["contenu"] == "465":
                return "<@&799267046574915644>", "<@&961558393447919627>"
            elif event[1]["contenu"] == "466":
                return "<@&799267103332368416>", "<@&961558407972786206>"
            elif event[1]["contenu"] == "467":
                return "<@&799267147519229952>", "<@&961558421210026035>"
            elif event[1]["contenu"] == "5":  # hôpital 10
                return "<@&799267202557280276>", "<@&961558437534249000>"
            elif event[1]["contenu"] == "215":  # écuries 2
                return "<@&799266481551441950>", "<@&961557929557917746>"
            elif event[1]["contenu"] == "226":  # écuries 3
                return "<@&799266534077890610>", "<@&961557999078490122>"
            elif event[1]["contenu"] == "456":  # douves 1
                return "<@&799267381925904395>", "<@&961558836974587914>"
            elif event[1]["contenu"] == "831":  # douves 2
                return "<@&799267437681442827>", "<@&961558870579380224>"
        elif event[0] == "75":
            if event[1]["contenu"] == "[2]":  # contremaître pain
                return "<@&961603178787373086>", "<@&961623169486159872>"
            elif event[1]["contenu"] == "[6]":  # maraudeur
                return "<@&961603183719882832>", "<@&961623119066431488>"
            elif event[1]["contenu"] == "[10]":  # sergent instructeur
                return "<@&961603187272458252>", "<@&961625064304959489>"
        elif event[0] == "90":
            caddie = event[1]["contenu"].strip("[]").replace(" ", "").split(",")
            caddie = [caddie[0:6], caddie[6:12], caddie[12:18]]
            nb_passes = 0
            for cote in caddie:
                for type_option in cote:
                    option = next(filter(lambda obj: (obj["typeID"] == type_option), self.donnees["shoppingCarts"]))
                    reward = next(filter(lambda obj: (obj["rewardID"] == option["rewardID"]), self.donnees["rewards"]))
                    if reward.get("add60MinSkip") or reward.get("add30MinSkip"):
                        nb_passes += 1
                        break
            if nb_passes == 3:
                return "<@&1073618582254125126>", "<@&1073619021783634000>"
        elif event[0] == "999" and int(event[1]["contenu"]) >= 200:  # 200% vert
            return f"<@&772138513323917382> Promo de {event[1]['contenu']}%", f"<@&772138513323917382> Prime time of {event[1]['contenu']}%"
        elif event[0] == "998" and int(event[1]["contenu"]) >= 200:  # 200% RE
            return f"<@&841978302562172969> Promo de {event[1]['contenu']}%", f"<@&841978302562172969> Prime time of {event[1]['contenu']}%"
        elif event[0] == "997" and int(event[1]["contenu"]) >= 200:  # 200% Lacis
            return f"<@&841978439329644606> Promo de {event[1]['contenu']}%", f"<@&841978439329644606> Prime time of {event[1]['contenu']}%"


async def getVersion(fichier):
    async with aiohttp.ClientSession() as session:
        if fichier == "item":
            async with session.get("https://empire-html5.goodgamestudios.com/default/items/ItemsVersion.properties") as response:
                return (await response.text()).split("=")[1]
        elif fichier == "item_test":
            async with session.get("https://empire-html5.goodgamestudios.com/openBeta/items/ItemsVersion.properties") as response:
                return (await response.text()).split("=")[1]
        elif fichier == "text":
            async with session.get("https://langserv.public.ggs-ep.com/12/fr/@metadata") as response:
                return str((await response.json())["@metadata"]["versionNo"])
        elif fichier == "text_dev":
            async with session.get("https://langserv-dev.public.ggs-ep.com/12/fr/@metadata") as response:
                return str((await response.json())["@metadata"]["versionNo"])
        elif fichier == "text_api":
            async with session.get("https://translations-api-live.public.ggs-ep.com/12/fr/versionNo") as response:
                return str((await response.json())["versionNo"])
        elif fichier == "text_api_test":
            async with session.get("https://translations-api-test.public.ggs-ep.com/12/fr/versionNo") as response:
                return str((await response.json())["versionNo"])
        elif fichier == "dll":
            async with session.get("https://empire-html5.goodgamestudios.com/default/index.html") as response:
                return re.findall("(?<=dll/ggs[.]dll[.]).*?(?=[.]js)", await response.text())[0]
        elif fichier == "dll_test":
            async with session.get("https://empire-html5.goodgamestudios.com/openBeta/index.html") as response:
                return re.findall("(?<=dll/ggs[.]dll[.]).*?(?=[.]js)", await response.text())[0]


async def getFile(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return response
