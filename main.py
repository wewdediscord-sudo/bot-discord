import discord
from discord.ext import commands
import asyncio
import os
import random
from flask import Flask
from threading import Thread

# ==========================================
# 1. CONFIGURATION DU SERVEUR WEB (KEEP ALIVE)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "I am alive! WESBOT is running."

def run_web():
    # Utilise la variable d'environnement PORT fournie par l'hébergeur (Render)
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# ==========================================
# 2. CONFIGURATION DU BOT DISCORD
# ==========================================

TOKEN = os.getenv('TOKEN') 

PROTECTED_USER_ID = 378883673640009728 # TON ID (Bypass Vocal)

# ID du salon où le message de départ sera envoyé
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
intents.members = True # ESSENTIEL pour détecter les départs
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

kick_loop_users = {}

# --- FONCTION DE VÉRIFICATION TROLL ---
async def troll_check(ctx):
    if ctx.author.id in TROLL_USER_IDS: 
        response = random.choice(TROLL_RESPONSES)
        await ctx.send(response)
        return True
    return False

# --- FONCTION DE VÉRIFICATION VOCALE ---
async def is_user_in_voice_channel(ctx):
    """Vérifie si l'auteur est en vocal, sauf s'il s'agit de l'ID protégé."""
    
    # Bypass pour l'utilisateur protégé
    if ctx.author.id == PROTECTED_USER_ID:
        return True
        
    # Vérification normale pour tous les autres utilisateurs
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("mdrrr tchorizooo tu las ou pas jsuis une galèreeee")
        return False
        
    return True

# --- ÉVÉNEMENT : DÉPART D'UN MEMBRE ---
@bot.event
async def on_member_remove(member):
    """Se déclenche quand quelqu'un quitte le serveur."""
    channel = bot.get_channel(LEAVE_CHANNEL_ID)
    
    if channel:
        # Envoie le message dans le salon spécifique
        await channel.send(f"{member.mention} a trahis la honda 🕵️‍♂️ ou autre qui sait 😂")
    else:
        print(f"ERREUR : Impossible de trouver le salon avec l'ID {LEAVE_CHANNEL_ID}")

# --- ÉVÉNEMENT : MESSAGES (ANTI-SPAM) ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # CORRECTION ICI : Utilisation de 'in' au lieu de '==' car WES_SPAMMER_IDS est une liste
    if message.author.id in WES_SPAMMER_IDS:
        content = message.content.lower()
        
        is_mentioning_me = f"<@{PROTECTED_USER_ID}>" in content
        
        is_triggering_word = any(keyword in content for keyword in WES_KEYWORDS)
        
        if is_mentioning_me or is_triggering_word:
            try:
                await message.channel.send("tg jeremerde ou t'es mute")
                return # Bloque le traitement de la commande
            except discord.Forbidden:
                print("ouille pas la permission")

    # Traite le message comme une commande (pour !kickloop, !machine, etc.)
    await bot.process_commands(message)

@bot.event
async def on_ready():
    if bot.user:
        print(f'Connecté en tant que {bot.user.name} ({bot.user.id})')
    bot.loop.create_task(kick_loop_task())

async def kick_loop_task():
    await bot.wait_until_ready()
    print("Démarrage de la tâche de surveillance vocale...")

    while not bot.is_closed():
        users_to_check = list(kick_loop_users.items())

        for user_id, member in users_to_check:
            if member.voice and member.voice.channel:
                try:
                    print(f"Déconnexion forcée de {member.display_name} du salon {member.voice.channel.name}")
                    await member.move_to(None)
                except discord.HTTPException as e:
                    print(f"Erreur lors de la déconnexion de {member.display_name}: {e}")
                except Exception as e:
                    print(f"Erreur inattendue pour {member.display_name}. Retrait de la liste. {e}")
                    if user_id in kick_loop_users:
                        del kick_loop_users[user_id]

        await asyncio.sleep(0.5)

# --- Commandes ---

@bot.command(name='kickloop')
async def kick_loop(ctx, member: discord.Member):
    if await troll_check(ctx): return 
    if not await is_user_in_voice_channel(ctx): return 

    if member.id == PROTECTED_USER_ID:
        await ctx.send("mdrrr oui oui aller")
        return

    if member.id in kick_loop_users:
        await ctx.send(f"❌ **{member.display_name}** est déjà sous surveillance 'kickloop'.")
        return

    kick_loop_users[member.id] = member
    await ctx.send(f"✅ **{member.display_name}** a été mis sous surveillance 'kickloop'. Il sera instantanément déconnecté de tout salon vocal.")

@bot.command(name='unkick')
async def unkick(ctx, member: discord.Member):
    if await troll_check(ctx): return 
    if not await is_user_in_voice_channel(ctx): return 

    if member.id not in kick_loop_users:
        await ctx.send(f"❌ **{member.display_name}** n'est pas sous surveillance 'kickloop'.")
        return

    del kick_loop_users[member.id]
    await ctx.send("liberableee")

@bot.command(name='machine')
async def machine_command(ctx, member: discord.Member, channel1: discord.VoiceChannel = None, channel2: discord.VoiceChannel = None):
    if await troll_check(ctx): return 
    if not await is_user_in_voice_channel(ctx): return 

    # VÉRIFICATION CIBLE (DOIT ÊTRE EN VOCAL)
    if not member.voice or not member.voice.channel:
        await ctx.send(f"❌ **{member.display_name}** aiii il est pas dans un vocal!!")
        return

    original_channel = member.voice.channel

    if not channel1 or not channel2:
        voice_channels = [c for c in ctx.guild.voice_channels if c != original_channel]
        if len(voice_channels) < 2:
            await ctx.send("❌ Vous devez spécifier deux salons vocaux cibles valides (`!machine @utilisateur #channel1 #channel2`), ou il doit y avoir au moins deux autres salons vocaux disponibles sur le serveur.")
            return

        if not channel1: channel1 = voice_channels[0]
        
        channel2_found = False
        for vc in voice_channels:
            if vc.id != channel1.id:
                channel2 = vc
                channel2_found = True
                break
        if not channel2_found:
            await ctx.send("❌ Veuillez spécifier deux salons différents.")
            return

    await ctx.send("meeeeemmmmm meeemmmm machine vroum")

    for i in range(5):
        try:
            await member.move_to(channel1, reason=f"Commande !machine ({i*2 + 1}/10)")
            await asyncio.sleep(0.5)

            await member.move_to(channel2, reason=f"Commande !machine ({i*2 + 2}/10)")
            await asyncio.sleep(0.5)

        except discord.HTTPException as e:
            if member.voice is None:
                await ctx.send(f" **{member.display_name}** a quitté le canal vocal. Machine arrêtée après {i*2 + 2} déplacements.")
                return
            await ctx.send(f"⚠️ Erreur lors du déplacement de **{member.display_name}**: {e}. Machine arrêtée.")
            return

    try:
        if member.voice is not None:
            await member.move_to(original_channel, reason="Commande !machine terminée")
            await ctx.send(f"✅ 'Machine' terminée ! **{member.display_name}** est de retour dans **{original_channel.name}**.")
        else:
            await ctx.send(f"✅ 'Machine' terminée. **{member.display_name}** a été déconnecté.")
    except discord.HTTPException as e:
        await ctx.send(f"⚠️ Erreur finale lors du déplacement de **{member.display_name}**: {e}.")

# ==========================================
# LANCEMENT
# ==========================================

keep_alive()
if TOKEN is None:
    print("ERREUR: TOKEN non défini. Veuillez configurer le secret 'TOKEN'.")
else:
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("ERREUR: Le TOKEN est invalide.")
    except discord.PrivilegedIntentsRequired:
        print("ERREUR: Les 'Intents' privilégiées (Server Members Intent) ne sont pas activées sur le portail développeur.")
