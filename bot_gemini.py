import discord
from discord.ext import commands
import google.generativeai as genai
import os
import asyncio

# Configuración
DISCORD_TOKEN = os.environ['DISCORD_TOKEN']
GEMINI_API_KEY = os.environ['GEMINI_API_KEY']

# Configurar Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Configurar intents CORREGIDOS
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

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

@bot.command()
async def ask(ctx, *, pregunta):
    if len(pregunta) > 500:
        await ctx.send("❌ La pregunta es muy larga. Máximo 500 caracteres.")
        return
    
    async with ctx.typing():
        respuesta = await gemini_mgr.get_response(pregunta)
        
        if len(respuesta) > 2000:
            chunks = [respuesta[i:i+2000] for i in range(0, len(respuesta), 2000)]
            for chunk in chunks:
                await ctx.send(chunk)
        else:
            await ctx.send(f"🤖 {respuesta}")

@bot.command()
async def stats(ctx):
    await ctx.send(f"📊 Total de requests: {gemini_mgr.total_requests}")

@bot.command()
async def clear(ctx):
    gemini_mgr.chat = gemini_mgr.model.start_chat(history=[])
    await ctx.send("🧹 Historial de conversación limpiado")

# EJECUCIÓN
try:
    bot.run(DISCORD_TOKEN)
except Exception as e:
    print(f"❌ Error: {e}")