import re
import threading
import queue
import random
import discord
from discord.ext import commands
from discord.utils import get
import pyttsx3
from discord_key import DISCORD_KEY

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
blacklist = [ 'http', '```[^`]*```' ]

# regex because it's probably the only relatively efficient way to do partial matching
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
re_blklst = re.compile('(?:^|\\s+)([^\\s]*(?:' + '|'.join('(?:{})'.format(each) for each in blacklist) + ')[^\\s]*)')

# structure queued data as a dictionary with keys for voice, rate_variance, and message
queue = queue.Queue()

async def on_message(message):
    if message.channel.name == "verification": 
        await message.delete()
        return
    if (message.author.id == bot.user.id or message.content[0]=='!'): return
    print('{0.author}: {0.content}'.format(message))

    random.seed(message.author.id)
    queue.put({
        "voice": 1 if get(message.guild.roles, name="Zira") in message.author.roles else 0,
        "rate_variance": int((random.random() * 50) - 25),
        "message": re.sub(re_blklst, " ", message.clean_content)
    })

bot = commands.Bot(command_prefix='!')
bot.add_listener(on_message, 'on_message')

@bot.command()
async def ping(ctx):
    await ctx.send('pong')
    
@bot.command()
async def zira(ctx):
    role = get(ctx.guild.roles, name="Zira")
    if(role in ctx.author.roles):
        await ctx.author.remove_roles(role)
    else:
        await ctx.author.add_roles(role)
        
@bot.command()
async def verify(ctx):
    role = get(ctx.guild.roles, name="Verified")
    if not (role in ctx.author.roles):
        await ctx.author.add_roles(role)
        chat = get(bot.get_all_channels(), name="chat")
        await chat.send(ctx.author.display_name + ' joined.')

tts_thread = TTSThread(queue)

bot.run(DISCORD_KEY)