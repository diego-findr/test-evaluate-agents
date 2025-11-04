# 🏗️ MAS-Eval: Documentación de Arquitectura

## Índice
1. [Visión General](#visión-general)
2. [Arquitectura de Agentes](#arquitectura-de-agentes)
3. [Flujo de Datos](#flujo-de-datos)
4. [Modelos Pydantic](#modelos-pydantic)
5. [Prompts de los Agentes](#prompts-de-los-agentes)
6. [Lógica de Decisión](#lógica-de-decisión)
7. [Manejo de Errores](#manejo-de-errores)

---

## Visión General

MAS-Eval es un sistema multiagente que implementa el patrón **Chain-of-Thought** y **Structured Output** para evaluar la compatibilidad candidato-oferta. El diseño prioriza:

- ✅ **Especialización:** Cada agente se enfoca en un dominio específico
- ✅ **Trazabilidad:** Cada decisión es justificada y auditable
- ✅ **Calidad:** Sistema de QA automático detecta inconsistencias
- ✅ **Escalabilidad:** Arquitectura lista para paralelización y caching

---

## Arquitectura de Agentes

### 1. Agentes Evaluadores (Parallelizable)

#### Agent 1: Technical Skills Evaluator
**Responsabilidad:** Evaluar competencias técnicas del candidato.

**Criterios de Evaluación:**
- Match de skills mandatorias (peso alto)
- Skills nice-to-have (peso medio)
- Profundidad técnica en la especialización
- Relevancia de la experiencia técnica

**Restricciones del Prompt:**
- NO evaluar cultura o soft skills
- NO evaluar progresión de carrera
- SOLO enfocarse en capacidades técnicas

**Peso en Score Final:** 50%

#### Agent 2: Career Trajectory Evaluator
**Responsabilidad:** Analizar la trayectoria profesional.

**Criterios de Evaluación:**
- Progresión de roles y responsabilidades
- Años de experiencia vs. requisitos
- Relevancia de empresas previas
- Estabilidad laboral y consistencia

**Restricciones del Prompt:**
- NO evaluar skills técnicas específicas
- NO evaluar personalidad o cultura
- SOLO enfocarse en la carrera profesional

**Peso en Score Final:** 35%

#### Agent 3: Cultural Fit Evaluator
**Responsabilidad:** Valorar alineación cultural y logística.

**Criterios de Evaluación:**
- Preferencias de trabajo (remote/hybrid/on-site)
- Match de idiomas requeridos
- Compatibilidad con tipo de empresa
- Flexibilidad y adaptabilidad

**Restricciones del Prompt:**
- NO evaluar skills técnicas
- NO evaluar experiencia o trayectoria
- SOLO enfocarse en fit cultural y logístico

**Peso en Score Final:** 15%

### 2. Agentes Finalizadores (Secuencial)

#### Agent 4: Scoring & Decision Agent
**Responsabilidad:** Calcular score final y tomar decisión binaria.

**Fórmula de Scoring:**
```python
final_score = (technical * 0.50) + (trajectory * 0.35) + (cultural * 0.15)
liked = final_score >= 70
```

**Outputs:**
- `final_score`: int (0-100)
- `liked`: boolean
- `aggregated_reason`: string (síntesis de las 3 evaluaciones)

#### Agent 5: QA Validation Agent
**Responsabilidad:** Detectar inconsistencias críticas.

**Reglas de Inconsistencia:**

**Regla 1:** LIKED con Technical Bajo
```python
if final_score >= 70 and technical_score < 50:
    qa_required_human_review = True
    # Riesgo: Candidato carece de base técnica fundamental
```

**Regla 2:** REJECTED con Consenso Alto
```python
if final_score < 70 and all([tech > 80, traj > 80, cult > 80]):
    qa_required_human_review = True
    # Riesgo: Ponderación rechaza a candidato excelente
```

**Outputs:**
- `qa_required_human_review`: boolean
- `qa_note`: string (explicación de la inconsistencia)

---

## Flujo de Datos

### Diagrama de Secuencia

```
Cliente → FastAPI Endpoint
            ↓
      EvaluationRequest
      (offer + candidate)
            ↓
   ┌──────────────────┐
   │ EvaluationState  │
   │ (LangGraph State)│
   └──────────────────┘
            ↓
   ┌──────────────────┐
   │ Technical Agent  │ → ScoreOutput(score=90, reason="...")
   └──────────────────┘
            ↓
   ┌──────────────────┐
   │ Trajectory Agent │ → ScoreOutput(score=82, reason="...")
   └──────────────────┘
            ↓
   ┌──────────────────┐
   │ Cultural Agent   │ → ScoreOutput(score=78, reason="...")
   └──────────────────┘
            ↓
   ┌──────────────────┐
   │ Scoring Agent    │ → ScoringAgentOutput(final_score=85, liked=true, ...)
   └──────────────────┘
            ↓
   ┌──────────────────┐
   │ QA Agent         │ → QAAgentOutput(qa_required_human_review=false, ...)
   └──────────────────┘
            ↓
      EvaluationResult
            ↓
   JSON Response → Cliente
```

### Estado del Grafo (EvaluationState)

El estado mantiene todos los datos a través del workflow:

```python
class EvaluationState(BaseModel):
    # Inputs
    offer: OfferData
    candidate: CandidateData
    
    # Agent 1 outputs
    technical_score: Optional[int] = None
    technical_reason: Optional[str] = None
    
    # Agent 2 outputs
    trajectory_score: Optional[int] = None
    trajectory_reason: Optional[str] = None
    
    # Agent 3 outputs
    cultural_score: Optional[int] = None
    cultural_reason: Optional[str] = None
    
    # Agent 4 outputs
    final_score: Optional[int] = None
    liked: Optional[bool] = None
    aggregated_reason: Optional[str] = None
    
    # Agent 5 outputs
    qa_required_human_review: Optional[bool] = None
    qa_note: Optional[str] = None
```

---

## Modelos Pydantic

### Input Models

#### OfferData
```python
{
  "job_title": str,              # REQUIRED
  "company_name": str,           # REQUIRED
  "mandatory_skills": [str],     # Key para Technical Agent
  "experience_required": str,    # Key para Trajectory Agent
  "mandatory_languages": [str],  # Key para Cultural Agent
  ...
}
```

#### CandidateData
```python
{
  "heading": str,                # REQUIRED
  "experience_years": int,       # REQUIRED
  "skills": [Skill],             # Key para Technical Agent
  "experiences": [Experience],   # Key para Trajectory Agent
  "languages": [Language],       # Key para Cultural Agent
  ...
}
```

### Output Model

#### EvaluationResult
```python
{
  "liked": bool,                    # Decisión binaria
  "reason": str,                    # Explicación final (prioriza QA)
  "compatibility": int,             # Score final (0-100)
  "ai_swipe_reasons": [str],        # Razones de los 4 agentes
  "models_liked": int,              # Siempre 5
  "models_evaluated": int,          # Siempre 5
  "qa_required_human_review": bool  # Flag de inconsistencia
}
```

---

## Prompts de los Agentes

### Estructura de Prompts

Todos los prompts siguen la estructura:

```
SYSTEM PROMPT:
- Identificación del rol especializado
- Áreas de enfoque EXCLUSIVAS
- Restricciones explícitas (qué NO evaluar)
- Guía de scoring con rangos y criterios

USER PROMPT:
- Datos de la oferta (contextualizados al rol del agente)
- Datos del candidato (contextualizados al rol del agente)
- Instrucción de evaluación específica
```

### Ventajas del Enfoque

1. **Especialización:** Cada agente es experto en su dominio
2. **Reducción de Bias:** Restricciones evitan evaluación fuera de scope
3. **Consistencia:** Structured Output garantiza formato parseable
4. **Trazabilidad:** Cada decisión tiene reasoning explícito

---

## Lógica de Decisión

### Sistema de Ponderación

La fórmula de scoring refleja las prioridades del negocio:

```
Final Score = (Technical × 50%) + (Trajectory × 35%) + (Cultural × 15%)
```

**Justificación de Pesos:**

- **50% Technical:** La competencia técnica es el factor crítico de éxito
  - Un candidato sin skills mandatorias no puede realizar el trabajo
  - Skills técnicas son objetivamente verificables

- **35% Trajectory:** La experiencia relevante predice desempeño
  - Candidatos con trayectoria sólida se adaptan más rápido
  - Progresión de carrera indica capacidad de crecimiento

- **15% Cultural:** El fit cultural es importante pero no crítico
  - La cultura se puede adaptar con tiempo
  - Idiomas y preferencias de trabajo son más flexibles

### Umbral de Decisión

```python
THRESHOLD = 70  # Basado en análisis de datos históricos

if final_score >= 70:
    liked = True   # Candidato aprobado
else:
    liked = False  # Candidato rechazado
```

**Calibración del Umbral:**
- 70+ indica que el candidato cumple con los requisitos esenciales
- Permite cierta flexibilidad en áreas menos críticas
- Balanceo entre precisión y recall (no rechazar buenos candidatos)

### Sistema de QA

El agente de QA actúa como **red de seguridad** para capturar:

1. **False Positives:** Candidatos aprobados sin competencia técnica base
2. **False Negatives:** Candidatos excelentes rechazados por edge cases

Cuando se detecta inconsistencia:
- Sistema marca `qa_required_human_review = True`
- Workflow continúa (no bloquea)
- Decisión final se mantiene, pero se alerta para revisión manual

---

## Manejo de Errores

### Jerarquía de Excepciones

```python
MASEvalException                    # Base exception
├── AgentExecutionError            # Error en ejecución de agente
├── InvalidInputDataError          # Error de validación Pydantic
└── GraphExecutionError            # Error en workflow LangGraph
```

### Estrategia de Error Handling

#### Nivel 1: Validación de Input (FastAPI + Pydantic)
```python
@app.post("/evaluate")
async def evaluate_candidate(request: EvaluationRequest):
    # Pydantic valida automáticamente
    # Si falla → HTTP 422 Unprocessable Entity
```

#### Nivel 2: Ejecución de Agentes (Try-Catch)
```python
try:
    result = await structured_llm.ainvoke(messages)
except Exception as e:
    logger.error(f"Agent failed: {e}")
    raise AgentExecutionError(f"Agent failed: {e}")
```

#### Nivel 3: Global Exception Handler (FastAPI)
```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, ...)
```

### Logging Estructurado

Todos los eventos se loguean con contexto:

```python
logger.info(f"Executing {agent_name}...")
logger.info(f"{agent_name} completed successfully")
logger.error(f"{agent_name} execution failed: {str(e)}")
```

**Niveles de Log:**
- `INFO`: Eventos normales del workflow
- `WARNING`: Situaciones anómalas pero no críticas
- `ERROR`: Fallos que impiden completar operación

---

## Optimizaciones Futuras

### 1. Paralelización Real

**Actual:** Agentes ejecutan secuencialmente
```python
workflow.add_edge("technical_agent", "trajectory_agent")
workflow.add_edge("trajectory_agent", "cultural_agent")
```

**Optimizado:**
```python
workflow.set_entry_point("fanout_node")
workflow.add_conditional_edges(
    "fanout_node",
    lambda _: ["technical", "trajectory", "cultural"],
    {
        "technical": "technical_agent",
        "trajectory": "trajectory_agent",
        "cultural": "cultural_agent"
    }
)
workflow.add_edge(["technical_agent", "trajectory_agent", "cultural_agent"], "scoring_agent")
```

**Mejora esperada:** Reducción de latencia de ~15s a ~5s

### 2. Caching de Evaluaciones

**Estrategia:**
```python
cache_key = hash(f"{offer.job_title}:{candidate.heading}:{candidate.experience_years}")
if cache.exists(cache_key):
    return cache.get(cache_key)
```

**Mejora esperada:** Hit rate ~30% en producción

### 3. Batch Processing

Para evaluar múltiples candidatos contra una oferta:
```python
@app.post("/evaluate-batch")
async def evaluate_batch(offer: OfferData, candidates: list[CandidateData]):
    tasks = [evaluate(EvaluationRequest(offer=offer, candidate=c)) for c in candidates]
    return await asyncio.gather(*tasks)
```

---

## Apéndice: Decisiones de Diseño

### ¿Por qué LangGraph y no LangChain Expression Language?

**LangGraph** permite:
- Estado mutable persistente entre nodos
- Checkpointing para debugging
- Visualización del grafo de ejecución
- Escalabilidad a workflows más complejos

### ¿Por qué Structured Output?

**Structured Output** garantiza:
- Respuestas parseables sin regex o post-processing
- Validación automática con Pydantic
- Reducción de errores de parsing
- Mejor experiencia de desarrollo

### ¿Por qué un solo archivo?

**Decisión:** Código en `main.py` para facilitar deploy inicial

**Ventajas:**
- Deploy simple en Cloud Run (un solo archivo)
- Fácil de revisar y auditar
- Menos complejidad de imports

**Tradeoff:** En producción, considerar modularizar en:
- `models.py`: Pydantic models
- `agents.py`: Agent implementations
- `graph.py`: LangGraph workflow
- `main.py`: FastAPI app

---

## Referencias

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [Pydantic v2 Migration](https://docs.pydantic.dev/latest/migration/)
- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
