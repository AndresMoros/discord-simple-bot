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

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

class GeminiManager:
    def __init__(self):
        # USAR GEMINI 2.0 FLASH
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.chat = self.model.start_chat(history=[])
        self.total_requests = 0

    async def get_response(self, prompt):
        try:
            self.total_requests += 1
            print(f"📨 Enviando: {prompt[:50]}...")
            
            # Usar generate_content en vez de send_message para mejor compatibilidad
            response = await asyncio.to_thread(
                self.model.generate_content, 
                prompt
            )
            
            if response.text:
                print("✅ Respuesta recibida de Gemini 2.0 Flash")
                return response.text
            else:
                return "❌ No recibí respuesta. Intenta de nuevo."
                
        except Exception as e:
            print(f"❌ Error con Gemini 2.0 Flash: {e}")
            return "❌ Error temporal. Intenta más tarde."

gemini_mgr = GeminiManager()

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')
    print('🤖 Usando Google Gemini 2.0 Flash (Más rápido)')
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ Sincronizados {len(synced)} comandos slash")
    except Exception as e:
        print(f"❌ Error sincronizando comandos: {e}")

@bot.tree.command(name="ask", description="Haz una pregunta al bot con IA")
@app_commands.describe(pregunta="Escribe tu pregunta aquí")
async def ask(interaction: discord.Interaction, pregunta: str):
    if len(pregunta) > 500:
        await interaction.response.send_message("❌ La pregunta es muy larga. Máximo 500 caracteres.", ephemeral=True)
        return
    
    await interaction.response.defer()
    respuesta = await gemini_mgr.get_response(pregunta)
    await interaction.followup.send(f"🤖 {respuesta}")

@bot.tree.command(name="stats", description="Muestra estadísticas del bot")
async def stats(interaction: discord.Interaction):
    await interaction.response.send_message(f"📊 Total de requests: {gemini_mgr.total_requests}")

@bot.tree.command(name="clear", description="Limpia el historial de conversación")
async def clear(interaction: discord.Interaction):
    gemini_mgr.chat = gemini_mgr.model.start_chat(history=[])
    await interaction.response.send_message("🧹 Historial limpiado")

# EJECUCIÓN
try:
    bot.run(DISCORD_TOKEN)
except Exception as e:
    print(f"❌ Error ejecutando el bot: {e}")