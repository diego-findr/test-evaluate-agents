# 🚀 MAS-Eval: Microservicio Multiagente de Evaluación de Candidatos

## 💡 Visión General del Proyecto

**MAS-Eval** (Multi-Agent System for Candidate Evaluation) es un microservicio de alta precisión diseñado para reemplazar la lógica de evaluación de candidatos (`handleOfferSwipe`) en el backend de Supabase. Utiliza una arquitectura de **cinco (5) Agentes de IA especializados** orquestados por **LangGraph** para realizar una evaluación holística (Técnica, Trayectoria, Cultural, Scoring y QA), garantizando una decisión de *swipe* más precisa y justificable.

El servicio está construido con **Python 3.11**, **FastAPI**, **LangGraph** y **OpenAI GPT-4o-mini**, siguiendo los estándares de **Clean Code / Senior A++** para ser desplegado en **Google Cloud Run**.

### ✨ Características Principales

- ✅ **Arquitectura Multiagente:** 5 agentes especializados (3 evaluadores + 2 finalizadores)
- ✅ **LangGraph Workflow:** Orquestación de agentes con nodos paralelos y secuenciales
- ✅ **Structured Output:** Pydantic schemas para respuestas consistentes y parseables
- ✅ **Weighted Scoring:** Sistema de ponderación inteligente (50% técnico, 35% trayectoria, 15% cultural)
- ✅ **QA Validation:** Detección automática de inconsistencias críticas
- ✅ **Type-Safe:** Type hints completos y validación estricta con Pydantic
- ✅ **Cloud-Ready:** Dockerizado y optimizado para Google Cloud Run
- ✅ **Production-Grade:** Error handling robusto, logging estructurado, DI con FastAPI

---

## 🏗️ Arquitectura y Componentes Clave

### 1. Arquitectura del Grafo (LangGraph)

El flujo de evaluación se divide en tres fases utilizando **Nodos Paralelos** y **Secuenciales**:

```
START
  ↓
[Technical Agent] → [Trajectory Agent] → [Cultural Agent]
  ↓                      ↓                      ↓
  └──────────────────────┴──────────────────────┘
                         ↓
              [Scoring Agent]
                         ↓
              [QA Validation Agent]
                         ↓
                        END
```

| Fase | Agentes Involucrados | Ejecución | Peso | Objetivo |
| :--- | :--- | :--- | :---: | :--- |
| **Evaluación Especializada** | Technical Skills Agent | Paralelo* | 50% | Evaluar competencias técnicas y match de skills |
| **Evaluación Especializada** | Career Trajectory Agent | Paralelo* | 35% | Analizar progresión profesional y experiencia |
| **Evaluación Especializada** | Cultural Fit Agent | Paralelo* | 15% | Valorar alineación cultural y preferencias |
| **Scoring & Decisión** | Scoring Agent | Secuencial | - | Aplicar ponderación y decidir like/reject |
| **Validación QA** | QA Validation Agent | Secuencial | - | Detectar inconsistencias críticas |

*Nota: Implementado secuencialmente en esta versión, pero la arquitectura soporta paralelización futura.

### 2. Lógica de Decisión Explícita

#### 2.1 Fórmula de Scoring Ponderado

```
Final Score = (Technical × 0.50) + (Trajectory × 0.35) + (Cultural × 0.15)
```

**Pesos por Agente:**
- **Aptitud Técnica:** 50% — Máxima prioridad en skills mandatorias
- **Ajuste de Trayectoria:** 35% — Experiencia relevante y progresión
- **Ajuste Cultural:** 15% — Work style y comunicación

#### 2.2 Regla Binaria de Decisión

```python
liked = True  if final_score >= 70  else False
```

#### 2.3 Reglas de QA Crítica

El agente de QA marca `qa_required_human_review = True` si detecta:

1. **Inconsistencia Tipo 1:** `final_score >= 70` (LIKED) pero `technical_score < 50`
   - *Riesgo:* Candidato carece de competencia técnica fundamental

2. **Inconsistencia Tipo 2:** `final_score < 70` (REJECTED) pero **todos** los scores individuales `> 80`
   - *Riesgo:* Posible edge case donde el promedio ponderado no refleja el consenso

### 3. Modelos de Datos (Pydantic)

El código utiliza modelos Pydantic estrictos con validación en tiempo de ejecución:

#### 3.1 Entrada (`EvaluationRequest`)
- **OfferData:** Job title, company, skills (mandatory/nice-to-have), languages, requirements
- **CandidateData:** Heading, years of experience, educations, experiences, skills, languages

#### 3.2 Salida (`EvaluationResult`)
```json
{
  "liked": true | false,
  "reason": "Explicación final priorizando nota de QA",
  "compatibility": 0-100,
  "ai_swipe_reasons": ["Razón Técnica", "Razón Trayectoria", "Razón Cultural", "Nota QA"],
  "models_liked": 5,
  "models_evaluated": 5,
  "qa_required_human_review": true | false
}
```

---

## ⚙️ Instalación y Configuración

### 1. Requisitos Previos

- **Python:** 3.11+
- **OpenAI API Key:** Cuenta activa en OpenAI
- **Docker** (opcional, para despliegue en contenedor)
- **Google Cloud SDK** (opcional, para despliegue en Cloud Run)

### 2. Instalación Local

```bash
# Clonar el repositorio
git clone <repository-url>
cd workspace

# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env y agregar tu OPENAI_API_KEY
```

### 3. Variables de Entorno

El servicio utiliza `pydantic-settings` para cargar configuración de manera tipada:

| Variable | Descripción | Valor por Defecto |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | Clave de API de OpenAI (requerido) | - |
| `OPENAI_MODEL` | Modelo de OpenAI a utilizar | `gpt-4o-mini` |
| `OPENAI_TEMPERATURE` | Temperatura del LLM (0.0-1.0) | `0.2` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |

**Archivo `.env` de ejemplo:**
```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.2
LOG_LEVEL=INFO
```

---

## 🚀 Ejecución

### 1. Modo Desarrollo (con Test Automático)

El archivo `main.py` incluye un bloque de prueba que se ejecuta automáticamente antes de iniciar el servidor:

```bash
python main.py
```

Esto ejecutará:
1. ✅ **Test del workflow** con datos mock de alta fidelidad
2. ✅ Ejecución completa del grafo de 5 agentes
3. ✅ Visualización de resultados detallados en logs
4. 🚀 **Inicio del servidor FastAPI** en `http://0.0.0.0:8080`

**Salida esperada del test:**
```
================================================================================
TESTING MAS-EVAL WORKFLOW WITH MOCK DATA
================================================================================

📋 EVALUATING:
   Position: Senior Full-Stack Developer
   Company: TechCorp Innovation Labs
   Candidate: Senior Full-Stack Engineer | Python & React Specialist
   Experience: 7 years

[INFO] Executing Technical Skills Agent...
[INFO] Executing Career Trajectory Agent...
[INFO] Executing Cultural Fit Agent...
[INFO] Executing Scoring Agent...
[INFO] Executing QA Validation Agent...

================================================================================
🎯 EVALUATION RESULTS
================================================================================

✅ Decision: LIKED ❤️
📊 Compatibility Score: 85/100
⚠️  Human Review Required: NO

📝 Final Reason:
[Razón agregada del scoring agent...]

🤖 Agent Evaluations:
1. Technical Skills (90/100): [Razón...]
2. Career Trajectory (82/100): [Razón...]
3. Cultural Fit (78/100): [Razón...]
4. QA Validation: [Nota...]

================================================================================
✅ TEST COMPLETED SUCCESSFULLY
================================================================================

🚀 Launching FastAPI server...
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### 2. Modo Producción (solo servidor)

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

### 3. Despliegue con Docker

```bash
# Build imagen
docker build -t mas-eval:latest .

# Run contenedor
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=your_key_here \
  mas-eval:latest
```

### 4. Despliegue en Google Cloud Run

```bash
# Opción 1: Script automatizado
./deploy.sh your-project-id europe-west1

# Opción 2: Comandos manuales
gcloud builds submit --tag gcr.io/PROJECT_ID/mas-eval
gcloud run deploy mas-eval \
  --image gcr.io/PROJECT_ID/mas-eval \
  --platform managed \
  --region europe-west1 \
  --set-env-vars OPENAI_API_KEY=your_key_here
```

---

## 💻 Uso del API

### Endpoint Principal: `POST /evaluate`

**URL:** `http://localhost:8080/evaluate`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "offer": {
    "job_title": "Senior Full-Stack Developer",
    "company_name": "TechCorp",
    "contract": "full-time",
    "type": "hybrid",
    "description": "We are seeking an experienced developer...",
    "salary_range": "€60,000 - €80,000",
    "responsibilities": "Design and develop scalable applications...",
    "experience_required": "5+ years",
    "mandatory_skills": ["Python", "React", "PostgreSQL"],
    "nice_to_have_skills": ["TypeScript", "GraphQL"],
    "mandatory_languages": ["English", "Spanish"],
    "nice_to_have_languages": ["German"],
    "preferred_companies": ["Google", "Amazon"],
    "extra_requirements_to_consider": "AI/ML experience is a plus"
  },
  "candidate": {
    "heading": "Senior Full-Stack Engineer | Python & React Specialist",
    "experience_years": 7,
    "educations": [
      {
        "degree": "Master of Science",
        "name": "Computer Science",
        "institute": "Universidad Politécnica de Madrid"
      }
    ],
    "experiences": [
      {
        "role": "Senior Full-Stack Developer",
        "company": "InnovateTech Solutions",
        "description": "Led development of cloud-based SaaS platform...",
        "duration": "4 years"
      }
    ],
    "skills": [
      {"name": "Python", "level": "Expert"},
      {"name": "React", "level": "Expert"},
      {"name": "PostgreSQL", "level": "Advanced"}
    ],
    "languages": [
      {"name": "Spanish", "level": "native"},
      {"name": "English", "level": "fluent"}
    ]
  }
}
```

**Response 200 OK:**
```json
{
  "liked": true,
  "reason": "El candidato demuestra una sólida aptitud técnica con dominio experto en Python y React...",
  "compatibility": 85,
  "ai_swipe_reasons": [
    "Technical Skills (90/100): Excellent match with all mandatory skills...",
    "Career Trajectory (82/100): Strong career progression...",
    "Cultural Fit (78/100): Languages and work style align well...",
    "QA Validation: No critical inconsistencies detected."
  ],
  "models_liked": 5,
  "models_evaluated": 5,
  "qa_required_human_review": false
}
```

### Endpoint de Health Check: `GET /health`

```bash
curl http://localhost:8080/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "mas-eval",
  "version": "1.0.0"
}
```

### Ejemplos con cURL

```bash
# Test de health check
curl http://localhost:8080/health

# Evaluación completa
curl -X POST http://localhost:8080/evaluate \
  -H "Content-Type: application/json" \
  -d @sample_request.json
```

---

## 🧪 Testing y Desarrollo

### 1. Test Automático Integrado

El archivo `main.py` incluye una función `test_evaluation_workflow()` que:

- ✅ Crea datos mock de alta fidelidad (oferta + candidato realistas)
- ✅ Ejecuta el workflow completo de 5 agentes
- ✅ Valida que todos los agentes respondan correctamente
- ✅ Muestra resultados detallados en logs estructurados

**Para ejecutar solo el test:**
```python
# Modificar main.py temporalmente:
if __name__ == "__main__":
    asyncio.run(test_evaluation_workflow())
    # Comentar la línea de uvicorn.run()
```

### 2. Mocks de Datos

Los mocks incluidos representan:
- **Oferta:** Senior Full-Stack Developer con 7 mandatory skills
- **Candidato:** 7 años de experiencia, educación sólida, portfolio relevante

### 3. Logs Estructurados

El sistema genera logs detallados para debugging:
```
[INFO] Executing Technical Skills Agent...
[INFO] Technical Skills Agent completed successfully
[INFO] Executing Career Trajectory Agent...
[INFO] Career Trajectory Agent completed successfully
...
```

---

## 📊 Arquitectura de Código (Clean Code A++)

El código está organizado en **11 secciones lógicas** dentro de `main.py`:

1. **Configuration & Logging:** Settings con pydantic-settings, logging setup
2. **Custom Exceptions:** Jerarquía de excepciones para error handling
3. **Input Data Models:** OfferData, CandidateData, EvaluationRequest
4. **Agent Output & State Models:** ScoreOutput, EvaluationState, EvaluationResult
5. **Agent Implementations:** AgentFactory con 5 agentes especializados
6. **LangGraph Builder:** GraphBuilder para construir el workflow
7. **Service Layer:** EvaluationService para ejecutar el grafo
8. **Dependency Injection:** DependencyContainer con lifecycle management
9. **FastAPI Application:** App setup, endpoints, error handlers
10. **Mock Data:** Función `create_mock_data()` con datos realistas
11. **Main Entry Point:** Test execution + server startup

### Principios Aplicados

- ✅ **SoC (Separation of Concerns):** Cada sección tiene responsabilidad única
- ✅ **DRY (Don't Repeat Yourself):** AgentFactory reutiliza lógica común
- ✅ **Type Safety:** Type hints completos, Pydantic models en todo
- ✅ **Dependency Injection:** FastAPI Depends() para servicios
- ✅ **Error Handling:** Custom exceptions + try-catch en capas
- ✅ **Async/Await:** Concurrencia nativa para llamadas LLM
- ✅ **Logging:** Structured logging con niveles apropiados

---

## 🔧 Troubleshooting

### Error: `OPENAI_API_KEY not found`

**Solución:**
```bash
# Verificar que .env existe y contiene la key
cat .env

# O exportar directamente
export OPENAI_API_KEY=sk-...
python main.py
```

### Error: `Evaluation service not initialized`

**Causa:** El servidor se inició antes de que se completara la inicialización.

**Solución:** Esperar a ver el log `All dependencies initialized successfully` antes de hacer requests.

### Respuestas lentas del API

**Causa:** Las llamadas a OpenAI pueden tardar 5-15 segundos.

**Optimización:** Considerar aumentar `--workers` en producción o implementar caching de evaluaciones.

---

## 📈 Roadmap y Mejoras Futuras

- [ ] **Paralelización real** de los 3 agentes evaluadores (actualmente secuencial)
- [ ] **Caching** de evaluaciones para candidatos repetidos
- [ ] **Metrics & Monitoring** con Prometheus/Grafana
- [ ] **A/B Testing** framework para comparar diferentes prompts
- [ ] **Webhooks** para notificaciones asíncronas
- [ ] **Multi-LLM support** (Anthropic Claude, local LLMs)
- [ ] **Fine-tuning** de modelos con data histórica de decisiones

---

## 📄 Licencia

Este proyecto es propiedad de [Tu Empresa] y está protegido bajo los términos de uso internos.

---

## 👥 Contribuciones

Para contribuir al proyecto:

1. Fork el repositorio
2. Crea una rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add amazing feature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

**Estándares de código:**
- Seguir PEP 8 y type hints obligatorios
- Tests unitarios para nuevos agentes
- Documentación actualizada en README

---

## 📞 Soporte

Para preguntas o issues:
- 📧 Email: tech-team@yourcompany.com
- 💬 Slack: #mas-eval-support
- 📝 Issues: GitHub Issues tab
