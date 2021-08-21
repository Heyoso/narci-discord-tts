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

# installed via Narrator settings on windows (windows key + control + N) and then also used Regedit to change Speech_OneCore/Voices to Speech/Voices.
std_list = ['David', 'Catherine', 'James', 'Linda', 'Richard', 'George', 'Susan', 'Sean', 'Heera', 'Ravi', 'Eva', 'Mark', 'Hazel', 'Zira']
secret_list = ['Raul', 'Sabina']
name_list = std_list + secret_list

# create the !setvocie usage without secret voices
setvoice_help = 'Use the command `!setvoice voicename` to set a voice. Valid voicenames are `'
setvoice_help += '`, `'.join(std_list) + "`"

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
    global role_cache
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
    voicename = None
    
    # set intersection between possible voice roles, and whatever role the author has.
    # empty set if user does not have any voice role,
    # list containing the user's voice role otherwise.
    prev = list(set(role_cache) & set(message.author.roles)) # less ugly? maybe
    if len(prev) == 0:
        voicename = random.choice(std_list)
    else:
        voicename = prev[0].name
        
    queue.put({
        "voice": voice_name_to_id[voicename],
        "rate_variance": rate,
        "message": remove_markdown(re.sub(re_blklst, " ", message.clean_content))
    })

role_cache = None
async def on_ready():
    global role_cache
    if role_cache is not None:
        return
    # this, of course, assumes only a single guild connected...
    role_cache = list(map(lambda nm : get(bot.guilds[0].roles, name=nm), name_list))
    print("role cache created.","OK" if len(set(role_cache) & set([None])) == 0 else "FAILED!")

bot = commands.Bot(command_prefix='!')
bot.add_listener(on_ready, 'on_ready')
bot.add_listener(on_message, 'on_message')


@bot.command()
@commands.guild_only()
async def ping(ctx):
    await ctx.send('pong')
    
@bot.command()
@commands.guild_only()
async def setvoice(ctx, v="default"):
    global role_cache
    v = v.capitalize()

    # is `v` a valid voice role?
    if get(role_cache, name=v) is not None:
        # does user have any previous voice roles? (should only ever be one...)
        prev = list(set(role_cache) & set(ctx.author.roles))
        if len(prev) > 0:
            # if so, remove it
            await ctx.author.remove_roles(*prev)
        # add the new voice role
        await ctx.author.add_roles(get(role_cache, name=v))
    else:
        # if not, just set the usage
        await ctx.send(setvoice_help)
        
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
