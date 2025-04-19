import discord,json
from discord.ext import commands
import asyncio,subprocess,yt_dlp
from asyncio.threads import to_thread
import time,random
from asyncio import Lock

from discord import ButtonStyle, Interaction
from discord.ui import Button, View

queued = []
lock = Lock()
voice = None
text_channel = None
current_playing = None
skip = False

def extractInfo(url):
    ydl_opts = {
        'quiet': True,  # Don't output any unnecessary info
        'extractaudio': False,  # We don't need to download the audio or video
        'default_search': 'ytsearch'  # Enables search if it's not a URL
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Extract video info
        info_dict = ydl.extract_info(url, download=False)

        if 'entries' in info_dict:
            info_dict = info_dict['entries'][0]
        
        # Video details:
        video_title = info_dict.get('title', 'Unknown Title')
        video_duration = info_dict.get('duration', 'Unknown Duration')  # Duration in seconds

        split = str(round(float(video_duration)/60,2)).split(".")
        video_duration = f"{split[0]}m {int((int(split[1])/100)*60)}s"

        # Print or return the video info
        print(f"Title: {video_title} Duration: {video_duration}")

        return {
            "title": video_title,
            "duration": video_duration,
            "url":info_dict['webpage_url']
        }

# def downloadMP3(jsondata):
#     ydl_opts = {
#         'format': 'bestaudio/best',
#         'outtmpl': f'queued/{jsondata["id"]}.mp3',  # Output path and file name
#         'postprocessors': [{  # Convert to mp3 using ffmpeg
#             'key': 'FFmpegExtractAudio',
#             'preferredcodec': 'mp3',
#             'preferredquality': '160',
#         }],
#         'quiet': False,  # Set True to suppress output
#     }
#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         ydl.download([jsondata['url']])

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
global bot
bot = commands.Bot(command_prefix='!',intents=intents)

# Slash Command Definition
@bot.tree.command(name="play", description="play a song")
async def playMusic(interaction: discord.Interaction, url_or_name: str):
    if not interaction.user.voice or not interaction.user.voice.channel:
        return await interaction.response.send_message(
            "❌ You must be in a voice channel to use this command!",
            ephemeral=True  # Only visible to the command user
        )
    
    # Get the voice channel
    voice_channel = interaction.user.voice.channel
    global voice,text_channel
    text_channel = interaction.channel
    if not voice:
        voice = await voice_channel.connect()
    await interaction.response.defer()

    json_data = extractInfo(url_or_name)
    async with lock:
        json_data["id"] = str(random.randint(0,10000000000000))
        queued.append(json_data)
        embed = discord.Embed(
            description=f"✅ Added {json_data["title"]} to queue"
        )
    await interaction.followup.send(embed=embed)

# # LT code
# # Slash Command Definition
# @bot.tree.command(name="queue", description="show the queue of songs")
# async def showQueue(interaction: discord.Interaction):
#     if not interaction.user.voice or not interaction.user.voice.channel:
#         return await interaction.response.send_message(
#             "❌ You must be in a voice channel to use this command!",
#             ephemeral=True
#         )

#     voice_channel = interaction.user.voice.channel
#     global voice

#     if not voice:
#         voice = await voice_channel.connect()

#     global queued  # Make sure this exists and is a list
#     if not queued:
#         return await interaction.response.send_message("current song" + c🚫 The queue is currently empty.")

#     queue_text = '\n'.join(f"{idx + 1}. {song['title']}" for idx, song in enumerate(queued))
#     await interaction.response.send_message(f"🎶 Current Queue:\n{queue_text}")
# #LT Code

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}!")
    # Syncing commands to Discord so they show up in the server
    # Sync commands to Discord so they appear
    try:
        await bot.tree.sync()  # Sync globally (for all servers)
        print("Slash commands synced globally.")
    except Exception as e:
        print(f"Error syncing commands: {e}")


async def server_clock():
    global voice,queued,current_playing
    while True:
        data = None
        async with lock:
            if(len(queued)!=0):
                data = queued.pop(0)
        if not data:
            await asyncio.sleep(2)
            continue
        await fetch_and_play(data)
def getURL(youtube_url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=False)
        url = info_dict['url']
        return url, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' 
        #return info_dict['url'], ydl._opener.headers['User-Agent']
async def fetch_and_play(json):
    global text_channel,current_playing,skip
    skip = False
    embed = discord.Embed(
        title="Current Playing",
        description=f"{json["title"]} ({json["duration"]})",
    )
    skipBtn = Button(label="⏭️ Skip", style=ButtonStyle.secondary)
    async def skipcall(interaction: Interaction):
        global skip
        skip = True
        await interaction.response.send_message("⏭️ Skipping track...", ephemeral=True)
    skipBtn.callback = skipcall
    view = View()
    view.add_item(skipBtn)
            
    sent = await text_channel.send(embed=embed,view=view)
    url, user_agent = getURL(json["url"])
    ffmpeg_options = {
        'before_options': f'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -user_agent "{user_agent}"',
        'options': '-vn'
    }
    voice.play(discord.FFmpegPCMAudio(url, **ffmpeg_options)) # this is asynchronus serverclock still runs
    current_playing = json
    while(voice.is_playing()):
        if(skip):
            break
        await asyncio.sleep(1)
    current_playing = None
    voice.stop()
    await sent.edit(view=None)

jindou_token=""
with open("a.json") as file:
    val = json.load(file)
    jindou_token = val["jindou_token"]
async def run_bot():
    await bot.start(jindou_token)
async def main():
    await asyncio.gather(
        run_bot(),
        server_clock()
    )

if __name__ == "__main__":
    asyncio.run(main())

