import re
import threading
import queue
import random
import discord
from discord.ext import commands
from discord.utils import get, remove_markdown
import pyttsx3
from discord_key import DISCORD_KEY
from datetime import date

voice_name_to_id = {}

name_list = ['David', 'Catherine', 'James', 'Linda', 'Richard', 'George', 'Susan', 'Sean', 'Heera', 'Ravi', 'Eva', 'Mark', 'Hazel', 'Zira', 'Raul', 'Sabina']
# installed via Narrator settings on windows (windows key + control + N) and then also used Regedit to change Speech_OneCore/Voices to Speech/Voices.

# handle TTS on a separate thread to not block bot while reading messages
class TTSThread(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue
        self.daemon = True
        self.start()
    def run(self):
        tts = pyttsx3.init()
        tts.setProperty('volume', 0.75)
        voices = tts.getProperty('voices')
        
        for i in range (len(voices)):
            print(voices[i].name)
            for n in name_list:
                if n in voices[i].name: 
                    voice_name_to_id[n] = i
                    break
        print (voice_name_to_id)
            
        tts.startLoop(False)
        running = True
        while running: # ok yea this runs forever maybe eventually handle shutdowns
            if self.queue.empty():
                tts.iterate()
            else:
                data = self.queue.get()
                tts.setProperty("voice", voices[data["voice"]].id)
                tts.setProperty("rate", 150 + data["rate_variance"])
                tts.say(data["message"])
        tts.endLoop()

# partial matches to filter. can be regex
blacklist = [
        'http',
        '```.*?```',
        '<[^\s]*>'
]

# regex because it's probably the only relatively efficient way to do partial matching
# (?si)         flags for DOT matches NEWLINE, and case insensitivity
# (?:^|\\s+)    begin looking at line start, or after any number of space
#                   characters. (match entire words, part 1.)
# (             begin a capture group. in this case, the entire word we want to
#                   partial match and potentially remove.
# [^\\s]*       capture any characters before a partial match (i.e. ensure the
#                   entire word is removed, part 1).
# (?:, '|'.join('(?:%s)' % p for p in blklst)), )
#               build a non-capture group for the partial matches from the
#                   blacklist. will expand into something like:
#                   (?:(?:foo)|(?:bar)|(?:baz))
# [^\\s]*       capture any characters after a partial match. (ensure the
#                   entire word is removed, part 2.) punctuation may get
#                   absorbed here idk if it matters.
re_blklst = re.compile('(?si)(?:^|\\s+)([^\\s]*(?:' + '|'.join('(?:{})'.format(each) for each in blacklist) + ')[^\\s]*)')

# structure queued data as a dictionary with keys for voice, rate_variance, and message
queue = queue.Queue()

async def on_message(message):
    if isinstance(message.channel, discord.channel.DMChannel):
        return
    if message.channel.name == "verification": 
        await message.delete()
        return
    
    if len(message.content) == 0:        return
    if message.author.id == bot.user.id: return
    if message.content[0]=='!':          return
    print('{0.author}: {0.clean_content}'.format(message))
    
    # logging
    with open('D:/discord_chat_logs/' + str(date.today()) + '.txt', 'a', encoding='utf-8') as f:
        f.write('{0.author}: {0.clean_content}\n'.format(message))
        f.close()

    random.seed(message.author.id)
    rate = int((random.random() * 50) - 25)
    thisvoice = -1
    
    for n in name_list:
        if get(message.guild.roles, name=n) in message.author.roles:
            thisvoice = voice_name_to_id[n]
            break;
    
    if thisvoice == -1:
        thisvoice = voice_name_to_id[name_list[random.randint(0, len(name_list)-3)]] #ugly hack to prevent spanish random roll
        
    queue.put({
        "voice": thisvoice,
        "rate_variance": rate,
        "message": remove_markdown(re.sub(re_blklst, " ", message.clean_content))
    })

bot = commands.Bot(command_prefix='!')
bot.add_listener(on_message, 'on_message')


@bot.command()
@commands.guild_only()
async def ping(ctx):
    await ctx.send('pong')
    
@bot.command()
@commands.guild_only()
@commands.has_role("Verified")
async def setvoice(ctx, v="default"):
    v = v.capitalize()
    role_list = list(map(lambda nm : get(ctx.guild.roles, name=nm), name_list))
    #if the voice you want, v, is in the role list, then assign that.
    if get(ctx.guild.roles, name=v) in role_list:
        for r in role_list: # find any voice role user already has (in the role list) and remove it.
            if r in ctx.author.roles:
                await ctx.author.remove_roles(r) # removed.
                break # should only have one of these so no need to continue this loop
        await ctx.author.add_roles(get(ctx.guild.roles, name=v)) # assign new role.
    else:
        chat = get(bot.get_all_channels(), name="chat")
        chatmsg = 'Use the command `!setvoice voicename` to set a voice. Valid voicenames are '
        for n in name_list:
            if (n == 'Raul') or (n == 'Sabina'):
                continue
            chatmsg += '`' + n + '`, '
        await chat.send(chatmsg)

@setvoice.error
async def setvoice_on_error(ctx, error):
    # ignore error when a user tries setvoice without the role
    if not isinstance(error, commands.MissingRole):
        # but we still care about other errors
        raise error
        
@bot.command()
@commands.guild_only()
async def verify(ctx):
    role = get(ctx.guild.roles, name="Verified")
    if not (role in ctx.author.roles):
        await ctx.author.add_roles(role)
        chat = get(bot.get_all_channels(), name="chat")
        await chat.send(ctx.author.display_name + ' joined.')

tts_thread = TTSThread(queue)

bot.remove_command('help')
bot.run(DISCORD_KEY)
