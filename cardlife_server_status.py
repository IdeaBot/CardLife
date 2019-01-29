from libs import plugin, embed, dataloader
import discord, traceback, datetime, os
import requests, json, os

CHANNEL = 'channel'
MESSAGE = 'message'
OFFICIAL_SERVERS = 'official_server_data'
MESSAGES = 'messagesloc'
UPTIMES = 'uptime_data'
DATAPATH = 'datapath'
MAX_TIMES = 4294967296
DIVISOR = 2

class Plugin(plugin.OnReadyPlugin):
    '''Displays pretty messages about the bot's status on the Idea Development Server

**Usage**
```@Idea add cardlife server status ```

For more information, do
```@Idea help cardlife_add_server_status``` '''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # constants
        self.public_namespace.SEEN_TIMES = 'seen'
        self.public_namespace.TOTAL_TIMES = 'total'
        # init data path
        if not os.path.isdir(self.config[DATAPATH]):
            os.mkdir(self.config[DATAPATH])
        # load server uptimes
        self.public_namespace.uptime_file = dataloader.loadfile_safe(self.config[UPTIMES], load_as='json')
        if not isinstance(self.public_namespace.uptime_file.content, dict):
            self.public_namespace.uptime_file.content = dict()
        self.public_namespace.uptime = self.public_namespace.uptime_file.content
        # load status messages
        self.public_namespace.messages_file = dataloader.loadfile_safe(self.config[MESSAGES], load_as='json')
        if not isinstance(self.public_namespace.messages_file.content, dict):
            self.public_namespace.messages_file.content = dict()
        self.public_namespace.messages = self.public_namespace.messages_file.content
        # load official servers
        self.official_servers_data = dataloader.loadfile_safe(self.config[OFFICIAL_SERVERS])
        if not isinstance(self.official_servers_data.content, dict):
            self.official_servers_data.content = dict()
        self.official_servers=self.official_servers_data.content

    async def action(self):
        try:
            # used to reset stuff while developing
            # (edit_message does weird stuff sometimes)
            # await self.edit_message(self.message, embed=embed.create_embed(description=''))
            try:
                # cardlife REST API queries
                # login to CardLife to get PublicId
                auth = requests.post("https://live-auth.cardlifegame.com/api/auth/authenticate", json={"EmailAddress":self.config["email"], "Password":self.config["password"]})
                auth_json = auth.json()
                # get information about all servers
                lobby = requests.post('https://live-lobby.cardlifegame.com/api/client/games', json={"PublicId":auth_json["PublicId"]})
                servers_json = lobby.json()

            except: # catch server errors
                # TODO: log failed server requests
                # print("Received invalid response from CardLife servers, skipping run...")
                return # skip run

            # create embed description
            self.record_uptime(servers_json["Games"])
            title = "CardLife Online Servers (%s)" %len(servers_json["Games"])
            description = ''
            highest_playercount=0
            for item in servers_json['Games']:
                playercount = '%s/%s'%(item['CurrentPlayers'], item['MaxPlayers'])
                if len(playercount)>highest_playercount:
                    highest_playercount=len(playercount)

            # create online server list str
            online_official_servers = dict()
            for item in servers_json['Games']:
                if item['IsOfficial']:
                    online_official_servers[str(item['Id'])]=item['WorldName']
                if not item['HasPassword']:
                    # create single line to describe server
                    playercount = '%s/%s'%(item['CurrentPlayers'], item['MaxPlayers'])
                    spaces = highest_playercount-len(playercount)
                    description+='`'+(spaces*'.')+playercount+'`| '
                    description+=''+item['WorldName']+''
                    if len(json.loads(item['ModInfo'])['orderedMods'])!=0:
                        description+=' (**M**)'
                    if item['HasPassword']: # contradiction; will never happen
                        description+=' (**P**)'
                    description+='\n'

            # create offline official server list
            offline_servers_str=''
            for id in self.official_servers:
                if id not in online_official_servers:
                    offline_servers_str+='**!** | '+self.official_servers[id]+'\n'
            for id in online_official_servers:
                self.official_servers[id]=online_official_servers[id] # update server names

            if offline_servers_str!='':
                description+='\n**__Offline__**\n'+offline_servers_str

            footer=dict()
            footer['text'] = '(Unofficial) CardLife API'
            footer['icon_url'] = None
            em = embed.create_embed(description=description, footer=footer, colour=0xddae60, title=title)
            for msg in self.public_namespace.messages:
                message = discord.Object(id=msg)
                message.channel = discord.Object(id=self.public_namespace.messages[msg])
                await self.edit_message(message, new_content=' ', embed=em)
            self.official_servers_data.content=self.official_servers
            self.official_servers_data.save()
        except:
            traceback.print_exc()
            pass
    def shutdown(self):
        # save data
        self.official_servers_data.content=self.official_servers
        self.official_servers_data.save()
        self.public_namespace.messages_file.content=self.public_namespace.messages
        self.public_namespace.messages_file.save()
        self.public_namespace.uptime_file.content=self.public_namespace.uptime
        self.public_namespace.uptime_file.save()

    def record_uptime(self, servers):
        for server in servers:
            if str(server["Id"]) not in self.public_namespace.uptime:
                self.public_namespace.uptime[str(server["Id"])] = {self.public_namespace.SEEN_TIMES:1, self.public_namespace.TOTAL_TIMES:0}
            else:
                self.public_namespace.uptime[str(server["Id"])][self.public_namespace.SEEN_TIMES] += 1
                if self.public_namespace.uptime[str(server["Id"])][self.public_namespace.TOTAL_TIMES]>MAX_TIMES:
                    self.public_namespace.uptime[str(server["Id"])][self.public_namespace.SEEN_TIMES] = self.public_namespace.uptime[str(server["Id"])][self.public_namespace.SEEN_TIMES] / DIVISOR
                    self.public_namespace.uptime[str(server["Id"])][self.public_namespace.TOTAL_TIMES] = self.public_namespace.uptime[str(server["Id"])][self.public_namespace.TOTAL_TIMES] / DIVISOR
        for server_id in self.public_namespace.uptime:
            self.public_namespace.uptime[server_id][self.public_namespace.TOTAL_TIMES] += 1
