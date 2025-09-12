import discord
from discord import app_commands
from discord.ext import commands
import google.generativeai as genai
import os
import asyncio

# Configuración
DISCORD_TOKEN = os.environ['DISCORD_TOKEN']
GEMINI_API_KEY = os.environ['GEMINI_API_KEY']

# Configurar Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Configurar intents
intents = discord.Intents.default()
intents.message_content = True

# Bot
bot = commands.Bot(command_prefix='!', intents=intents)

class GeminiManager:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-pro')
        self.chat = self.model.start_chat(history=[])
        self.total_requests = 0

    async def get_response(self, prompt):
        try:
            self.total_requests += 1
            response = await asyncio.to_thread(self.chat.send_message, prompt)
            return response.text
        except Exception as e:
            print(f"Error con Gemini: {e}")
            return "❌ Error al procesar tu pregunta."

gemini_mgr = GeminiManager()

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')
    print('🤖 Usando Google Gemini')
    try:
        synced = await bot.tree.sync()
        print(f"✅ Sincronizados {len(synced)} comandos slash")
    except Exception as e:
        print(f"❌ Error sincronizando comandos: {e}")

# COMANDO SLASH (/ask)
@bot.tree.command(name="ask", description="Haz una pregunta al bot")
async def ask(interaction: discord.Interaction, pregunta: str):
    if len(pregunta) > 500:
        await interaction.response.send_message("❌ La pregunta es muy larga. Máximo 500 caracteres.")
        return
    
    await interaction.response.defer()
    respuesta = await gemini_mgr.get_response(pregunta)
    
    if len(respuesta) > 2000:
        chunks = [respuesta[i:i+2000] for i in range(0, len(respuesta), 2000)]
        for chunk in chunks:
            await interaction.followup.send(chunk)
    else:
        await interaction.followup.send(f"🤖 {respuesta}")

# COMANDO DE PREFIJO (!stats)
@bot.command()
async def stats(ctx):
    await ctx.send(f"📊 Total de requests: {gemini_mgr.total_requests}")

# EJECUCIÓN
try:
    bot.run(DISCORD_TOKEN)
except Exception as e:
    print(f"❌ Error: {e}")