# 🚀 Setup Local de IA con Ollama

Guía paso-a-paso para configurar y usar Ollama localmente en tu máquina de desarrollo.

## ⚙️ Requisitos Previos

- **CPU**: Moderno (Core i5+, M1+, Ryzen 5+)
- **RAM**: Mínimo 8GB (16GB recomendado)
- **Espacio disco**: 5-20GB según modelo
- **SO**: Windows, macOS, Linux
- **Docker** (opcional, pero recomendado)

## 📦 Instalación

### Windows 10/11

#### Opción 1: Instalador (Recomendado)
1. Descarga: https://ollama.ai/download/windows
2. Ejecuta el instalador (.exe)
3. Sigue pasos de instalación
4. Se iniciará automáticamente como servicio
5. Verifica: Ollama debería estar en system tray

#### Opción 2: WSL2 + Linux
```bash
# En Windows Terminal (WSL2)
curl https://ollama.ai/install.sh | sh

# Ejecutar
ollama serve
```

### macOS

```bash
# Descargar
curl -L https://ollama.ai/download/mac -o ollama.dmg

# O descarga desde https://ollama.ai/download/mac

# Abrir e instalar
open ollama.dmg

# Ejecutar (con Spotlight)
cmd+space → Ollama
```

### Linux

```bash
# Ubuntu/Debian
curl https://ollama.ai/install.sh | sh

# Fedora/RHEL
curl https://ollama.ai/install.sh | sh

# Ejecutar
ollama serve
```

## 🤖 Descargar Modelos

### Desarrollo (Rápido)
```bash
# Llama 3.1 8B - Buena relación velocidad/calidad
ollama pull llama3.1:8b

# Tiempo: ~5 minutos
# Tamaño: ~5GB RAM
```

### Análisis (Potente)
```bash
# Llama 3.1 70B - Mejor calidad (necesita 16GB+ RAM)
ollama pull llama3.1:70b

# Tiempo: ~10 minutos
# Tamaño: ~45GB disco, 40GB RAM
```

### Alternativas Ligeras
```bash
# Mistral 7B - Rápido y compacto
ollama pull mistral:7b

# Neural Chat - Especializado en chat
ollama pull neural-chat:7b
```

### Ver Modelos Disponibles
```bash
ollama list
```

## ✅ Verificar Instalación

### 1. Servidor corriendo
```bash
# Verifica en http://localhost:11434
curl http://localhost:11434/api/tags
```

Debería retornar:
```json
{
  "models": [
    {
      "name": "llama3.1:8b",
      "modified_at": "...",
      "size": ...
    }
  ]
}
```

### 2. Generar respuesta rápida
```bash
# Test simple
ollama generate --model llama3.1:8b "Hola, ¿quién eres?"

# Debería retornar respuesta en ~5 segundos
```

## 🔧 Configurar GestiqCloud

### 1. Copiar configuración
```bash
cd apps/backend

# Copiar archivo de ejemplo
cp .env.ai.example .env.local

# O agregar a tu .env actual
```

### 2. Editar .env
```bash
# Asegúrate que tengas:
ENVIRONMENT=development
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TIMEOUT=30
```

### 3. Verificar variables cargadas
```bash
# Desde Python
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('OLLAMA_URL:', os.getenv('OLLAMA_URL'))
print('OLLAMA_MODEL:', os.getenv('OLLAMA_MODEL'))
"
```

## 🧪 Probar Integración

### 1. Test simple
```bash
# En directorio del proyecto
cd apps/backend

python3 << 'EOF'
import asyncio
from app.services.ai import AIService, AITask

async def test():
    response = await AIService.query(
        task=AITask.ANALYSIS,
        prompt="Soy un asistente de prueba. Responde con una frase corta.",
        temperature=0.3,
        max_tokens=100
    )
    
    if response.is_error:
        print(f"❌ Error: {response.error}")
    else:
        print(f"✅ Respuesta: {response.content}")
        print(f"⏱️ Tiempo: {response.processing_time_ms}ms")

asyncio.run(test())
EOF
```

### 2. Test en API
```bash
# Iniciar servidor (en otra terminal)
cd apps/backend
uvicorn app.main:app --reload

# En otra terminal, probar endpoint
curl -X GET http://localhost:8000/api/v1/health/ai

# Debería mostrar algo como:
# {
#   "status": "healthy",
#   "primary_provider": "ollama",
#   "providers": { "ollama": true, "ovhcloud": false, "openai": false }
# }
```

## 📊 Performance Tuning

### Si Ollama es lento:

1. **Aumentar número de threads**
```bash
# Linux/macOS
export OLLAMA_NUM_THREAD=8
ollama serve

# Windows - editar en Services
```

2. **GPU Acceleration** (si disponible)
```bash
# NVIDIA CUDA
# Ollama lo detecta automáticamente

# Apple Metal (macOS)
# Ya soportado nativamente en M1+
```

3. **Memoria**
```bash
# Si falta RAM, usar modelo más pequeño
ollama pull mistral:7b  # 4.7GB vs 5GB para llama3.1:8b
```

4. **MKeep-alive** (mantener modelo en RAM)
```bash
# Agregar a curl
curl -X POST http://localhost:11434/api/generate \
  -d '{"model":"llama3.1:8b","keep_alive":"24h"}'
```

## 🐳 Alternativa: Docker

Si tienes problemas locales:

```bash
# Descargar imagen (una sola vez)
docker pull ollama/ollama

# Ejecutar contenedor
docker run -d \
  --name ollama \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  ollama/ollama

# Descargar modelo dentro del contenedor
docker exec ollama ollama pull llama3.1:8b

# Usar como siempre en http://localhost:11434
```

## 📝 Troubleshooting

### "Connection refused"
```bash
# 1. Verificar que Ollama está corriendo
ollama serve

# 2. En otra terminal, probar
curl http://localhost:11434/api/tags

# 3. Si no funciona, reiniciar:
# Windows: Services > Restart Ollama
# macOS: killall ollama && ollama serve
# Linux: systemctl restart ollama
```

### "Out of memory"
```bash
# Usar modelo más pequeño
ollama pull mistral:7b

# O aumentar RAM disponible
# Editar settings de Ollama para limitar uso
```

### Respuesta muy lenta
```bash
# 1. Verificar CPU usage
# Debería usar 6-8 cores, si usa menos aumentar OLLAMA_NUM_THREAD

# 2. Cambiar modelo
ollama pull mistral:7b  # Más rápido

# 3. Reducir max_tokens en prompts
```

### Modelo no descarga
```bash
# Verificar espacio disco
df -h

# Espacio mínimo recomendado: 20GB

# Reintentar descarga
ollama pull llama3.1:8b --insecure
```

## 🎯 Optimizaciones para Producción (Nota)

Para producción usa OVHCloud (ver `AI_INTEGRATION_GUIDE.md`)

Ollama es para **desarrollo local solamente** porque:
- CPU no escala bien bajo carga
- No tiene autenticación
- No tiene rate limiting
- No es redundante

## 📚 Recursos

- Documentación Ollama: https://github.com/ollama/ollama
- Modelos disponibles: https://ollama.ai/library
- Discord community: https://discord.gg/ollama

## ✨ Tips

1. **Deja Ollama corriendo** en background todo el tiempo de desarrollo
2. **Cachea respuestas** para no hacer requests innecesarios
3. **Usa el modelo correcto**: 8B para desarrollo, 70B para análisis profundo
4. **Keep-alive**: Ollama mantiene modelo en RAM por defecto (con timeout)
5. **Monitor**: Verifica `/api/v1/health/ai` regularmente

## 🎓 Próximos Pasos

1. ✅ Ollama corriendo en localhost:11434
2. ✅ Configurado en .env
3. ✅ Testeado con health check
4. ➡️ **Integrar en Copilot** (ver `COPILOT_ENHANCEMENT.md`)

---

**Tiempo total**: ~20 minutos  
**Tamaño descarga**: ~5-10GB  
**RAM necesaria**: 8GB mínimo (16GB recomendado)

¿Tienes algún problema? Revisa la sección **Troubleshooting** arriba.
