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

# Listes de surveillance
kick_loop_users = {}
muted_users = [] # Liste pour ceux qui doivent "fermer leur gueule"

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
        await channel.send(f"{member.mention} a trahis la honda 🕵️‍♂️ ou autre qui sait 😂")
    else:
        print(f"ERREUR : Impossible de trouver le salon avec l'ID {LEAVE_CHANNEL_ID}")

# --- ÉVÉNEMENT : MESSAGES (LOGIQUE PRINCIPALE) ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # 1. GESTION DU MUTE TEXTUEL ("Fermer ta gueule")
    # Si l'utilisateur est dans la liste des mutés, on supprime son message direct
    if message.author.id in muted_users:
        try:
            await message.delete()
            return # On arrête tout ici, il ne peut rien faire
        except discord.Forbidden:
            pass # Si le bot ne peut pas supprimer, tant pis

    content = message.content.lower()

    # 2. DÉTECTION "TU VAS LA FERMER TA GUEULE"
    if "tu vas la fermer ta gueule" in content and message.mentions:
        victim = message.mentions[0]
        # Ajout à la liste de mute textuel
        if victim.id not in muted_users:
            muted_users.append(victim.id)
        
        # Mute Vocal
        if victim.voice:
            try:
                await victim.edit(mute=True)
            except: pass
        
        await message.channel.send(f"{victim.mention} FERME TA MEEEEERE")

    # 3. DÉTECTION DES BAFFES
    elif ("tiens une baffe" in content or "tiens 1 baffe" in content) and message.mentions:
        await apply_baffes(message, message.mentions[0], 1)
        
    elif "tiens 2 baffes" in content and message.mentions:
        await apply_baffes(message, message.mentions[0], 2)

    elif "tiens 3 baffes" in content and message.mentions:
        await apply_baffes(message, message.mentions[0], 3)

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

    # Traite le message comme une commande normale
    await bot.process_commands(message)

# --- FONCTION AUXILIAIRE POUR LES BAFFES ---
async def apply_baffes(message, member, count):
    if not member.voice or not member.voice.channel:
        # Si la victime n'est pas en vocal, ça ne marche pas
        await message.channel.send(f"La baffe part dans le vide... {member.display_name} n'est pas en vocal.")
        return

    original_channel = member.voice.channel
    # Récupérer tous les salons sauf l'actuel
    available_channels = [c for c in message.guild.voice_channels if c != original_channel]

    if not available_channels:
        await message.channel.send("Pas assez de salons pour donner des baffes !")
        return

    msg = await message.channel.send("prends cette baffe prends")

    # Boucle de déplacement
    for i in range(count):
        target_channel = random.choice(available_channels)
        try:
            await member.move_to(target_channel, reason="Prend ta baffe")
            await asyncio.sleep(0.5) # Temps de la baffe
        except:
            break # Stop si erreur (déco)
    
    # Retour au bercail
    try:
        await member.move_to(original_channel, reason="Fin des baffes")
    except:
        pass

# --- DEMARRAGE ---
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
                    print(f"Déconnexion forcée de {member.display_name}")
                    await member.move_to(None)
                except discord.HTTPException as e:
                    print(f"Erreur kickloop: {e}")
                except Exception as e:
                    print(f"Erreur kickloop inattendue: {e}")
                    if user_id in kick_loop_users:
                        del kick_loop_users[user_id]

        await asyncio.sleep(0.5)

# --- COMMANDES ---

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

    # --- VERIFICATION SELF-UNKICK ---
    if ctx.author.id == member.id and member.id in kick_loop_users:
        await ctx.send("mdr")
        return
    # --------------------------------

    if member.id not in kick_loop_users:
        await ctx.send(f"❌ **{member.display_name}** n'est pas sous surveillance 'kickloop'.")
        return

    del kick_loop_users[member.id]
    await ctx.send("liberableee")

# --- NOUVELLE COMMANDE : UNMUTE ---
@bot.command(name='unmute')
async def unmute(ctx, member: discord.Member):
    if await troll_check(ctx): return 
    if not await is_user_in_voice_channel(ctx): return 

    # 1. Retrait du mute textuel
    if member.id in muted_users:
        muted_users.remove(member.id)
    
    # 2. Retrait du mute vocal
    try:
        if member.voice:
            await member.edit(mute=False)
        await ctx.send(f"**{member.display_name}** a été unmute (vocal + écrit).")
    except Exception as e:
        # En cas d'erreur (ex: le bot n'a pas les perms ou l'user n'est pas en vocal)
        await ctx.send(f"J'ai enlevé le mute écrit, mais j'ai galéré sur le vocal.")

@bot.command(name='machine')
async def machine_command(ctx, member: discord.Member, channel1: discord.VoiceChannel = None, channel2: discord.VoiceChannel = None):
    if await troll_check(ctx): return 
    if not await is_user_in_voice_channel(ctx): return 

    if not member.voice or not member.voice.channel:
        await ctx.send(f"❌ **{member.display_name}** aiii il est pas dans un vocal!!")
        return

    original_channel = member.voice.channel

    if not channel1 or not channel2:
        voice_channels = [c for c in ctx.guild.voice_channels if c != original_channel]
        if len(voice_channels) < 2:
            await ctx.send("❌ Il faut au moins 2 autres salons pour faire la machine.")
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
            await member.move_to(channel1, reason=f"Machine ({i*2 + 1}/10)")
            await asyncio.sleep(0.5)

            await member.move_to(channel2, reason=f"Machine ({i*2 + 2}/10)")
            await asyncio.sleep(0.5)

        except discord.HTTPException:
            break

    try:
        if member.voice is not None:
            await member.move_to(original_channel, reason="Machine terminée")
            await ctx.send(f"✅ 'Machine' terminée !")
        else:
            await ctx.send(f"✅ 'Machine' terminée (déco).")
    except:
        pass

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
        print("ERREUR: Les 'Intents' privilégiées ne sont pas activées.")
