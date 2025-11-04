# 🚀 Quick Start Guide - MAS-Eval

Este documento proporciona los pasos más rápidos para ejecutar el microservicio de evaluación.

## ⚡ Inicio Rápido (5 minutos)

### 1. Instalar Dependencias

```bash
# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar paquetes
pip install -r requirements.txt
```

### 2. Configurar API Key

```bash
# Crear archivo .env
cp .env.example .env

# Editar .env y agregar tu API key de OpenAI
echo "OPENAI_API_KEY=sk-your-actual-key-here" > .env
```

### 3. Ejecutar Test + Servidor

```bash
# Esto ejecuta automáticamente:
# 1. Test con mock data
# 2. Servidor FastAPI en puerto 8080
python main.py
```

**Salida esperada:**
```
================================================================================
TESTING MAS-EVAL WORKFLOW WITH MOCK DATA
================================================================================
...
✅ TEST COMPLETED SUCCESSFULLY
================================================================================
🚀 Launching FastAPI server...
INFO:     Uvicorn running on http://0.0.0.0:8080
```

## 🧪 Probar el API

### Opción 1: Health Check

```bash
curl http://localhost:8080/health
```

**Respuesta:**
```json
{
  "status": "healthy",
  "service": "mas-eval",
  "version": "1.0.0"
}
```

### Opción 2: Evaluación Completa

```bash
curl -X POST http://localhost:8080/evaluate \
  -H "Content-Type: application/json" \
  -d @sample_request.json
```

**Respuesta esperada (~10-15 segundos):**
```json
{
  "liked": true,
  "reason": "El candidato demuestra sólida aptitud técnica...",
  "compatibility": 85,
  "ai_swipe_reasons": [
    "Technical Skills (90/100): Excellent match...",
    "Career Trajectory (82/100): Strong progression...",
    "Cultural Fit (78/100): Good alignment...",
    "QA Validation: No critical inconsistencies."
  ],
  "models_liked": 5,
  "models_evaluated": 5,
  "qa_required_human_review": false
}
```

## 🐳 Despliegue con Docker

```bash
# Build
docker build -t mas-eval:latest .

# Run
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=your_key_here \
  mas-eval:latest

# Test
curl http://localhost:8080/health
```

## ☁️ Despliegue en Google Cloud Run

```bash
# Configurar project ID
export GCP_PROJECT_ID=your-project-id

# Ejecutar script de deploy
./deploy.sh $GCP_PROJECT_ID europe-west1

# El script te mostrará la URL del servicio al finalizar
```

## 📊 Entender los Resultados

### Campos del Response

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `liked` | boolean | `true` si compatibility >= 70 |
| `reason` | string | Explicación final (prioriza nota QA si existe) |
| `compatibility` | int (0-100) | Score final ponderado |
| `ai_swipe_reasons` | string[] | Array con las 4 razones de los agentes |
| `models_liked` | int | Número de modelos de acuerdo (siempre 5) |
| `models_evaluated` | int | Total de modelos (siempre 5) |
| `qa_required_human_review` | boolean | Flag de inconsistencia crítica |

### Interpretación del Score

- **90-100:** Excelente match, candidato ideal
- **70-89:** Buen match, cumple requisitos
- **50-69:** Match moderado, considerar con reservas
- **30-49:** Match débil, probablemente rechazar
- **0-29:** Sin match, rechazar

### QA Human Review

Se activa (`true`) si:
1. Score >= 70 pero Technical < 50 (falta competencia base)
2. Score < 70 pero todos los scores individuales > 80 (edge case)

## 🔍 Troubleshooting Rápido

### Error: `pydantic_core._pydantic_core.ValidationError`

**Causa:** API key inválida o variables de entorno no cargadas.

**Solución:**
```bash
# Verificar .env
cat .env | grep OPENAI_API_KEY

# Exportar manualmente
export OPENAI_API_KEY=sk-...
python main.py
```

### Error: `ConnectionError` o timeout

**Causa:** Sin conexión a internet o firewall bloqueando OpenAI API.

**Solución:**
```bash
# Verificar conectividad
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Server lento (> 30 segundos por request)

**Causa:** Llamadas secuenciales a 5 agentes + latencia de red.

**Optimización:**
- Usar modelo más rápido: `OPENAI_MODEL=gpt-3.5-turbo`
- Reducir temperatura: `OPENAI_TEMPERATURE=0.0`
- Implementar caching (ver roadmap en README)

## 📚 Próximos Pasos

1. ✅ Lee el [README.md](README.md) completo para arquitectura detallada
2. ✅ Revisa `main.py` para entender la implementación
3. ✅ Modifica `sample_request.json` con tus propios datos
4. ✅ Integra el endpoint `/evaluate` en tu backend de Supabase

## 🆘 Ayuda

- 📖 Documentación completa: [README.md](README.md)
- 🐛 Reportar bug: Abrir issue en GitHub
- 💬 Soporte: tech-team@yourcompany.com
