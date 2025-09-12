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
            
            response = await asyncio.to_thread(
                self.model.generate_content, 
                prompt
            )
            
            if response.text:
                print(f"✅ Respuesta recibida ({len(response.text)} caracteres)")
                return response.text
            else:
                return "❌ No recibí respuesta. Intenta de nuevo."
                
        except Exception as e:
            print(f"❌ Error con Gemini: {e}")
            return "❌ Error temporal. Intenta más tarde."

gemini_mgr = GeminiManager()

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')
    print('🤖 Usando Google Gemini 2.0 Flash')
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ Sincronizados {len(synced)} comandos slash")
    except Exception as e:
        print(f"❌ Error sincronizando comandos: {e}")

def split_long_message(message, max_length=2000):
    """Divide mensajes largos en chunks de máximo max_length caracteres"""
    if len(message) <= max_length:
        return [message]
    
    chunks = []
    current_chunk = ""
    
    # Dividir por oraciones para no cortar palabras
    sentences = message.split('. ')
    for sentence in sentences:
        # Si agregar esta oración excede el límite, guardar el chunk actual
        if len(current_chunk) + len(sentence) + 2 > max_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
        
        # Agregar la oración al chunk actual
        if current_chunk:
            current_chunk += ". " + sentence
        else:
            current_chunk = sentence
    
    # Agregar el último chunk si queda algo
    if current_chunk:
        chunks.append(current_chunk + ".")
    
    return chunks

@bot.tree.command(name="ask", description="Haz una pregunta al bot con IA")
@app_commands.describe(pregunta="Escribe tu pregunta aquí")
async def ask(interaction: discord.Interaction, pregunta: str):
    if len(pregunta) > 500:
        await interaction.response.send_message("❌ La pregunta es muy larga. Máximo 500 caracteres.", ephemeral=True)
        return
    
    await interaction.response.defer()
    respuesta = await gemini_mgr.get_response(pregunta)
    
    # Si la respuesta es extremadamente larga, enviar como archivo
    if len(respuesta) > 4000:
        await interaction.followup.send("📝 Respuesta muy larga. Enviando como archivo...")
        
        # Crear archivo temporal
        with open("respuesta.txt", "w", encoding="utf-8") as f:
            f.write(f"Pregunta: {pregunta}\n\nRespuesta:\n{respuesta}")
        
        # Enviar archivo
        await interaction.followup.send(file=discord.File("respuesta.txt"))
        
        # Limpiar archivo temporal
        if os.path.exists("respuesta.txt"):
            os.remove("respuesta.txt")
        return
    
    # Dividir respuesta normal
    chunks = split_long_message(respuesta)
    chunks = chunks[:4]  # Máximo 4 chunks + mensaje inicial = 5 total (límite de Discord)
    
    # Enviar primer chunk
    await interaction.followup.send(f"🤖 {chunks[0]}")
    
    # Enviar chunks adicionales con delays
    for chunk in chunks[1:]:
        await asyncio.sleep(0.5)  # Delay para evitar rate limiting
        await interaction.followup.send(chunk)
    
    # Notificar si se truncó la respuesta
    if len(respuesta) > sum(len(chunk) for chunk in chunks):
        await interaction.followup.send("ℹ️ *La respuesta fue acortada por ser demasiado larga.*")

@bot.tree.command(name="stats", description="Muestra estadísticas del bot")
async def stats(interaction: discord.Interaction):
    await interaction.response.send_message(f"📊 Total de requests: {gemini_mgr.total_requests}")

@bot.tree.command(name="clear", description="Limpia el historial de conversación")
async def clear(interaction: discord.Interaction):
    gemini_mgr.chat = gemini_mgr.model.start_chat(history=[])
    await interaction.response.send_message("🧹 Historial de conversación limpiado")

# Manejo de errores global
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandInvokeError):
        await interaction.followup.send("❌ Error al procesar el comando. Intenta más tarde.", ephemeral=True)
        print(f"❌ Error en comando: {error}")

# EJECUCIÓN
try:
    bot.run(DISCORD_TOKEN)
except Exception as e:
    print(f"❌ Error ejecutando el bot: {e}")