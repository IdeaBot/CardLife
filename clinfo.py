from libs import command, embed
import re, requests, json

class Command(command.DirectOnlyCommand, command.Config):
    '''Retrieve CardLife server information about a specific server

**Usage**
```@Idea cardlife server info "<server>" ```
Where
**`<server>`** is an online server displayed in the CardLife server list

Please do not overuse this command - respect the CardLife servers'''
    def matches(self, message):
        return self.collect_args(message)!=None
    def collect_args(self, message):
        return re.search(r'(?:cardlife|cl)\s*server\s*info(?:rmation)?(?:\s*for)?\s+\"([^\"]+)\"', message.content, re.I)

    def action(self, message):
        yield from self.send_typing(message.channel)
        try:
            # cardlife REST API queries
            # login to CardLife to get PublicId
            auth = requests.post("https://live-auth.cardlifegame.com/api/auth/authenticate", json={"EmailAddress":self.config["email"], "Password":self.config["password"]})
            auth_json = auth.json()
            # get information about all servers
            lobby = requests.post('https://live-lobby.cardlifegame.com/api/client/games', json={"PublicId":auth_json["PublicId"]})
            lobby_json = lobby.json()
        except: # catch server errors
            # TODO: log failed server requests
            yield from self.send_message(message.channel, 'Unable to contact CardLife servers')
            return

        args = self.collect_args(message)
        name_id = args.group(1) # server name OR id

        server_info = self.find_name_or_id(name_id, lobby_json['Games'])
        # print(server_info)

        if server_info==None:
            yield from self.send_message(message.channel, 'Unable to find `%s`, maybe it\'s offline?' % name_id)
            return

        # fix for ModInfo returned as string instead of dict
        if isinstance(server_info['ModInfo'], str):
            server_info['ModInfo'] = json.loads(server_info['ModInfo'])

        # format server_info nicely
        is_modded=len(server_info['ModInfo']['orderedMods'])>0
        description = '**'
        if server_info['IsOfficial']==True:
            description+='Official '
        elif server_info['IsOfficial']==False:
            description+='Unofficial '
        if is_modded:
            description+='modded '
        if server_info['IsPvp']==True:
            description+='PVP '
        elif server_info['IsPvp']==False:
            description+='PVE '
        description+='server**\n'

        if is_modded:
            # description+='Mods: `'
            field_val3=''
            for mod in server_info['ModInfo']['orderedMods']:
                field_val3+=mod['name']
                if mod['metadata']['author']:
                    field_val3+=' by '+mod['metadata']['author']
                field_val3+='\n'
            field_val3=field_val3
            # description=description[:-2]+'`\n'

        description_end = \
        '''`{CurrentPlayers}/{MaxPlayers}` online @ {Ping}ms
Region: {0}
AntiCheat: {IsAntiCheatEnabled}
Password: {HasPassword}
`v{GameVersion}` | ID:`{Id}`'''

        # description += description_end.format(server_info["Region"].upper(), **server_info)

        server_info["Region"] = server_info["Region"].upper()
        if str(server_info['Id']) in self.public_namespace.uptime:
            seen, total = self.public_namespace.uptime[str(server_info['Id'])][self.public_namespace.SEEN_TIMES], self.public_namespace.uptime[str(server_info['Id'])][self.public_namespace.TOTAL_TIMES]
            server_info["Uptime"] = (seen/total)
        else:
            server_info["Uptime"] = 1

        # Connection info
        field_val1='''Players: `{CurrentPlayers}/{MaxPlayers}`
Uptime: `{Uptime:.0%}`
Ping: {Ping}ms
Region: {Region}
'''
        field_val1=field_val1.format(**server_info)

        # Security info
        field_val2='''AntiCheat: {IsAntiCheatEnabled}
Password: {HasPassword} '''
        field_val2=field_val2.format(**server_info)

        # Debug info
        field_val4=\
        '''ID:`{Id}`
`v{GameVersion}` '''
        field_val4=field_val4.format(**server_info)

        footer=dict()
        footer['text'] = '(Unofficial) CardLife API'
        footer['icon_url'] = None

        em = embed.create_embed(title=''+server_info['WorldName']+'', description=description, footer=footer, colour=0xddae60)
        em.add_field(name='Server Online', value=field_val1, inline=True)
        em.add_field(name='Security', value=field_val2, inline=True)
        if is_modded:
            em.add_field(name='Mods', value=field_val3, inline=True)
        em.add_field(name='Debug', value=field_val4, inline=is_modded)

        yield from self.send_message(message.channel, embed=em)

    def find_name_or_id(self, name_or_id, servers):
        for server in servers:
            if str(server['Id'])==name_or_id or server['WorldName']==name_or_id:
                return server
