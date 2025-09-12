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

    async def get_response(self, prompt, max_tokens=None):
        try:
            self.total_requests += 1
            print(f"📨 Enviando: {prompt[:50]}...")
            
            # Configuración de generación
            generation_config = {}
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            
            response = await asyncio.to_thread(
                self.model.generate_content, 
                prompt,
                generation_config=generation_config or None
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
        # Si la oración sola es demasiado larga, dividirla
        if len(sentence) > max_length - 100:  # Dejar margen
            words = sentence.split(' ')
            for word in words:
                if len(current_chunk) + len(word) + 1 > max_length:
                    if current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = ""
                if current_chunk:
                    current_chunk += " " + word
                else:
                    current_chunk = word
        else:
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
        # Asegurar que no exceda el límite
        if len(current_chunk) > max_length:
            chunks.append(current_chunk[:max_length])
            if len(current_chunk) > max_length:
                chunks.append(current_chunk[max_length:max_length*2])
        else:
            chunks.append(current_chunk)
    
    # Asegurar que ningún chunk exceda el límite
    final_chunks = []
    for chunk in chunks:
        while len(chunk) > max_length:
            final_chunks.append(chunk[:max_length])
            chunk = chunk[max_length:]
        final_chunks.append(chunk)
    
    return final_chunks

def ensure_short_response(response, max_length=1500):
    """Asegura que la respuesta no exceda el límite de un mensaje"""
    if len(response) <= max_length:
        return response
    
    # Truncar inteligentemente en un punto natural
    truncated = response[:max_length]
    
    # Encontrar el último punto completo
    last_period = truncated.rfind('.')
    if last_period > max_length * 0.7:  # Si hay un punto en el 70% final
        return truncated[:last_period + 1] + ".. (respuesta truncada)"
    else:
        return truncated + ".. (respuesta truncada)"

@bot.tree.command(name="ask", description="Haz una pregunta al bot con IA (respuesta completa)")
@app_commands.describe(pregunta="Escribe tu pregunta aquí")
async def ask(interaction: discord.Interaction, pregunta: str):
    if len(pregunta) > 500:
        await interaction.response.send_message("❌ La pregunta es muy larga. Máximo 500 caracteres.", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        respuesta = await gemini_mgr.get_response(pregunta)
        
        # DEBUG (después de obtener la respuesta)
        print(f"📏 Longitud de respuesta: {len(respuesta)} caracteres")
        
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
        chunks = chunks[:4]  # Máximo 4 chunks + mensaje inicial = 5 total
        
        # ✅ AGREGAR AQUÍ TAMBIÉN (después de dividir en chunks)
        print(f"📦 Número de chunks: {len(chunks)}")
        for i, chunk in enumerate(chunks):
            print(f"Chunk {i}: {len(chunk)} caracteres")
            # Verificación de seguridad
            if len(chunk) > 2000:
                print(f"❌ PELIGRO: Chunk {i} tiene {len(chunk)} caracteres (más de 2000!)")
                chunks[i] = chunk[:2000]  # Forzar truncamiento
                print(f"✅ Corregido: Chunk {i} ahora tiene {len(chunks[i])} caracteres")
        
        # Enviar primer chunk
        await interaction.followup.send(f"🤖 {chunks[0]}")
        
        # Enviar chunks adicionales con delays
        for chunk in chunks[1:]:
            await asyncio.sleep(0.5)
            if chunk.strip():  # Solo enviar si no está vacío
                await interaction.followup.send(chunk)
        
        # Notificar si se truncó la respuesta
        if len(respuesta) > sum(len(chunk) for chunk in chunks):
            await interaction.followup.send("ℹ️ *La respuesta fue acortada por ser demasiado larga.*")
            
    except Exception as e:
        print(f"❌ Error en comando ask: {e}")
        import traceback
        traceback.print_exc()  # ← Esto mostrará el error completo
        await interaction.followup.send("❌ Error al procesar tu pregunta. Intenta más tarde.")

@bot.tree.command(name="quick", description="Haz una pregunta con respuesta rápida y corta (1 mensaje máximo)")
@app_commands.describe(pregunta="Escribe tu pregunta para respuesta rápida")
async def quick(interaction: discord.Interaction, pregunta: str):
    if len(pregunta) > 300:
        await interaction.response.send_message("❌ La pregunta es muy larga. Máximo 300 caracteres.", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    # Prompt optimizado para respuestas cortas
    quick_prompt = f"Responde de forma extremadamente concisa y directa (máximo 1200 caracteres, sé breve y ve al punto): {pregunta}"
    
    respuesta = await gemini_mgr.get_response(quick_prompt, max_tokens=250)
    
    # Forzar respuesta corta
    respuesta_corta = ensure_short_response(respuesta, 1500)
    
    # Emoji de rayo para respuestas rápidas ⚡
    await interaction.followup.send(f"⚡ {respuesta_corta}")

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