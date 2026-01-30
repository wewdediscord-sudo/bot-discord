import discord
from discord.ext import commands
import asyncio
import os
import random
from flask import Flask
from threading import Thread
import time
import yt_dlp # Pour télécharger l'audio

# ==========================================
# 1. CONFIGURATION DU SERVEUR WEB (KEEP ALIVE)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "I am alive! WESBOT is running."

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# ==========================================
# 2. CONFIGURATION MUSIQUE (YT-DLP & FFMPEG)
# ==========================================
# Options pour simuler un navigateur et éviter les blocages YouTube
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': 'True',
    'quiet': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'source_address': '0.0.0.0',
}

# Options pour FFmpeg (reconnexion auto si coupure)
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# Variables globales pour la musique
music_queues = {} # File d'attente par serveur
loop_status = {}  # Statut de la boucle par serveur

# ==========================================
# 3. CONFIGURATION DU BOT DISCORD
# ==========================================

TOKEN = os.getenv('TOKEN') 

PROTECTED_USER_ID = 378883673640009728 

LEAVE_CHANNEL_ID = 1442640695956471898

TROLL_USER_IDS = [
    688837162719903747, 
    422002207584419840
]

WES_SPAMMER_IDS = [
    460863520821739542,
    688837162719903747
]
WES_KEYWORDS = ["wes", "wesley", "Wes", "Wesley"]

TROLL_RESPONSES = [
    "Et puis quoi encore mdrrr ton tacos au cacaboudin là",
    "Tg sale pute",
    "beeeeehh ça marche pas",
    "Tu me mettra un tacos à la mayo dans ma commande aussi connasse"
]

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True 
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# --- VARIABLES GLOBALES MODÉRATION ---
kick_loop_users = {}
muted_users = []
last_baffe_time = 0 

# --- FONCTIONS UTILES ---
async def troll_check(ctx):
    if ctx.author.id in TROLL_USER_IDS: 
        response = random.choice(TROLL_RESPONSES)
        await ctx.send(response)
        return True
    return False

async def is_user_in_voice_channel(ctx):
    if ctx.author.id == PROTECTED_USER_ID:
        return True
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("mdrrr tchorizooo tu las ou pas jsuis une galèreeee")
        return False
    return True

# --- LOGIQUE MUSIQUE (Callback après chaque chanson) ---
def play_next(ctx):
    guild_id = ctx.guild.id
    
    # Vérification : Est-ce qu'on doit boucler la musique actuelle ?
    if loop_status.get(guild_id, False):
        # On relance la même source (il faut recréer l'objet FFmpeg)
        # Note : Pour faire simple, le loop ici va réutiliser la dernière URL jouée si possible,
        # mais la méthode idéale serait de stocker l'URL actuelle.
        # Ici, si le loop est activé, on suppose qu'on ne dépile pas la queue.
        # Simplification : On reprend le premier élément sans le supprimer si loop
        pass 
        # (La logique de loop parfaite demande de stocker 'current_song'. 
        # Pour faire simple ici, on va gérer le loop dans la commande play ou via la queue).

    if guild_id in music_queues and len(music_queues[guild_id]) > 0:
        # Si loop activé, on reprend la même (index 0) sans la supprimer
        if loop_status.get(guild_id, False):
            url = music_queues[guild_id][0]['url']
            title = music_queues[guild_id][0]['title']
        else:
            # Sinon on passe à la suivante (on retire l'ancienne)
            song = music_queues[guild_id].pop(0)
            url = song['url']
            title = song['title']

        # Lecture
        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        ctx.voice_client.play(source, after=lambda e: play_next(ctx))
        
        # Petit message pour dire ce qui joue (Optionnel, attention au spam)
        # futur = asyncio.run_coroutine_threadsafe(ctx.send(f"🎵 En cours : **{title}**"), bot.loop)
        
    else:
        # PLUS DE MUSIQUE DANS LA FILE
        # On envoie le message demandé et on déco
        fut = asyncio.run_coroutine_threadsafe(ctx.send("musique terminée je décooo"), bot.loop)
        fut2 = asyncio.run_coroutine_threadsafe(ctx.voice_client.disconnect(), bot.loop)

# --- ÉVÉNEMENTS ---
@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVE_CHANNEL_ID)
    if channel:
        await channel.send(f"{member.mention} a trahis la honda 🕵️‍♂️ ou autre qui sait 😂")

@bot.event
async def on_message(message):
    global last_baffe_time 

    if message.author == bot.user:
        return

    # 1. MUTE TEXTUEL
    if message.author.id in muted_users:
        try:
            await message.delete()
            return 
        except discord.Forbidden:
            pass 

    content = message.content.lower()

    # 2. TU VAS LA FERMER TA GUEULE
    if "tu vas la fermer ta gueule" in content and message.mentions:
        victim = message.mentions[0]
        if victim.id not in muted_users:
            muted_users.append(victim.id)
        if victim.voice:
            try: await victim.edit(mute=True)
            except: pass
        await message.channel.send(f"C'est bon, {victim.mention} a été mute. Chut.")

    # 3. LES BAFFES
    elif "tiens" in content and "baffe" in content and message.mentions:
        if time.time() - last_baffe_time < 3: 
            return # Anti-spam

        last_baffe_time = time.time()
        
        count = 0
        is_glitch = False

        if "une baffe" in content or "1 baffe" in content: count = 1
        elif "2 baffes" in content: count = 2
        elif "3 baffes" in content: 
            count = 2 # BUG VOLONTAIRE
            is_glitch = True
        
        if count > 0:
            await apply_baffes(message, message.mentions[0], count, is_glitch)

    # 4. ANTI-SPAM WES
    elif message.author.id in WES_SPAMMER_IDS:
        is_mentioning_me = f"<@{PROTECTED_USER_ID}>" in content
        is_triggering_word = any(keyword in content for keyword in WES_KEYWORDS)
        
        if is_mentioning_me or is_triggering_word:
            try:
                await message.channel.send("tg jeremerde ou t'es mute")
                return 
            except discord.Forbidden:
                pass

    await bot.process_commands(message)

# --- LOGIQUE BAFFES ---
async def apply_baffes(message, member, count, is_glitch=False):
    if not member.voice or not member.voice.channel:
        await message.channel.send(f"La baffe part dans le vide... {member.display_name} n'est pas en vocal.")
        return

    original_channel = member.voice.channel
    await message.channel.send(f"👊 Et bim ! Baffes pour {member.display_name} !")

    for i in range(count):
        current_pos = member.voice.channel
        available_channels = [c for c in message.guild.voice_channels if c != current_pos]

        if not available_channels:
            break

        target_channel = random.choice(available_channels)
        try:
            await member.move_to(target_channel, reason=f"Baffe {i+1}")
            await asyncio.sleep(0.5) 
        except:
            break 
    
    try:
        if member.voice:
            await member.move_to(original_channel, reason="Fin des baffes")
    except: pass

    if is_glitch:
        await message.channel.send("C'est un bug ?")

# --- TÂCHE DE FOND ---
@bot.event
async def on_ready():
    if bot.user:
        print(f'Connecté en tant que {bot.user.name} ({bot.user.id})')
    bot.loop.create_task(kick_loop_task())

async def kick_loop_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        users_to_check = list(kick_loop_users.items())
        for user_id, member in users_to_check:
            if member.voice and member.voice.channel:
                try:
                    await member.move_to(None)
                except: pass 
        await asyncio.sleep(0.5)

# ==========================================
# 4. COMMANDES (MUSIQUE + MODÉRATION)
# ==========================================

@bot.command(name='play')
async def play(ctx, *, search: str):
    """Joue de la musique ou l'ajoute à la file."""
    if await troll_check(ctx): return
    if not await is_user_in_voice_channel(ctx): return

    # Connexion au salon vocal
    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)

    # Recherche et Téléchargement
    async with ctx.typing():
        try:
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                # Si c'est un lien ou une recherche
                query = search if search.startswith("http") else f"ytsearch:{search}"
                info = ydl.extract_info(query, download=False)
                
                # Si c'est une recherche, on prend le premier résultat
                if 'entries' in info:
                    info = info['entries'][0]
                
                url = info['url']
                title = info['title']
                
                # Gestion de la Queue
                if ctx.guild.id not in music_queues:
                    music_queues[ctx.guild.id] = []
                
                music_queues[ctx.guild.id].append({'url': url, 'title': title})
                
                # Si rien ne joue, on lance la machine
                if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                    # On lance la lecture via la fonction play_next
                    play_next(ctx)
                    await ctx.send(f"▶️ Lecture de : **{title}**")
                else:
                    await ctx.send(f"✅ Ajouté à la file : **{title}**")

        except Exception as e:
            await ctx.send(f"❌ Erreur musique : {e}")

@bot.command(name='stop')
async def stop(ctx):
    """Arrête la musique et déconnecte le bot."""
    if await troll_check(ctx): return
    if not await is_user_in_voice_channel(ctx): return

    if ctx.guild.id in music_queues:
        music_queues[ctx.guild.id] = [] # Vider la queue
    
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🛑 Musique stoppée, je me casse.")
    else:
        await ctx.send("Jsuis même pas connecté frère.")

@bot.command(name='loop')
async def loop(ctx):
    """Active ou désactive la boucle sur la musique actuelle."""
    if await troll_check(ctx): return
    if not await is_user_in_voice_channel(ctx): return

    guild_id = ctx.guild.id
    current_status = loop_status.get(guild_id, False)
    loop_status[guild_id] = not current_status # Inverse le statut
    
    if loop_status[guild_id]:
        await ctx.send("🔂 Loop activé ! La musique va tourner en boucle.")
    else:
        await ctx.send("➡️ Loop désactivé.")

@bot.command(name='kickloop')
@commands.cooldown(1, 3, commands.BucketType.user) 
async def kick_loop(ctx, member: discord.Member):
    if await troll_check(ctx): return 
    if not await is_user_in_voice_channel(ctx): return 

    if member.id == PROTECTED_USER_ID:
        await ctx.send("mdrrr oui oui aller")
        return

    if member.id in kick_loop_users:
        await ctx.send(f"❌ Déjà ciblé.")
        return

    kick_loop_users[member.id] = member
    await ctx.send(f"✅ **{member.display_name}** loopé.")

@bot.command(name='unkick')
@commands.cooldown(1, 2, commands.BucketType.user)
async def unkick(ctx, member: discord.Member):
    if await troll_check(ctx): return 
    if not await is_user_in_voice_channel(ctx): return 

    if ctx.author.id == member.id and member.id in kick_loop_users:
        await ctx.send("mdr")
        return

    if member.id not in kick_loop_users:
        await ctx.send(f"❌ Pas ciblé.")
        return

    del kick_loop_users[member.id]
    await ctx.send("liberableee")

@bot.command(name='unmute')
@commands.cooldown(1, 2, commands.BucketType.user)
async def unmute(ctx, member: discord.Member):
    if await troll_check(ctx): return 
    if not await is_user_in_voice_channel(ctx): return 

    if member.id in muted_users:
        muted_users.remove(member.id)
    
    try:
        if member.voice: await member.edit(mute=False)
        await ctx.send(f"C'est bon, **{member.display_name}** unmute.")
    except:
        await ctx.send(f"Unmute textuel ok, vocal erreur.")

@bot.command(name='machine')
@commands.cooldown(1, 10, commands.BucketType.user) 
async def machine_command(ctx, member: discord.Member, channel1: discord.VoiceChannel = None, channel2: discord.VoiceChannel = None):
    if await troll_check(ctx): return 
    if not await is_user_in_voice_channel(ctx): return 

    if not member.voice or not member.voice.channel:
        await ctx.send(f"❌ Pas en vocal.")
        return

    original_channel = member.voice.channel
    if not channel1 or not channel2:
        voice_channels = [c for c in ctx.guild.voice_channels if c != original_channel]
        if len(voice_channels) < 2:
            await ctx.send("❌ Pas assez de salons.")
            return
        if not channel1: channel1 = voice_channels[0]
        channel2_found = False
        for vc in voice_channels:
            if vc.id != channel1.id:
                channel2 = vc
                channel2_found = True
                break
        if not channel2_found:
            await ctx.send("❌ Erreur salons.")
            return

    await ctx.send("meeeeemmmmm meeemmmm machine vroum")

    for i in range(5):
        try:
            await member.move_to(channel1)
            await asyncio.sleep(0.5)
            await member.move_to(channel2)
            await asyncio.sleep(0.5)
        except: break

    try: await member.move_to(original_channel)
    except: pass
    await ctx.send(f"✅ Machine terminée !")

# ==========================================
# LANCEMENT
# ==========================================

keep_alive()
if TOKEN is None:
    print("ERREUR: TOKEN manquant.")
else:
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Erreur: {e}")
