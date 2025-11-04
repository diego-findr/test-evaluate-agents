"""
🚀 MAS-Eval: Microservicio Multiagente de Evaluación de Candidatos

Microservicio de evaluación de candidatos utilizando LangGraph con 5 agentes especializados:
- 3 Evaluadores en paralelo: Técnico, Trayectoria, Cultural
- 1 Agente de Scoring: Pondera las evaluaciones y decide liked/reject
- 1 Agente de Validación (QA): Valida coherencia de la decisión

Autor: Generated for MAS-Eval
Python: 3.11+
Framework: FastAPI + LangGraph + LangChain
"""

import asyncio
import logging
from typing import Literal, TypedDict

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.pydantic_v1 import BaseModel as LangChainBaseModel
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# ============================================================================
# CONFIGURACIÓN Y LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Configuración del servicio usando pydantic-settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    openai_api_key: str = Field(..., description="OpenAI API Key")
    openai_model: str = Field(default="gpt-4o-mini", description="Modelo de OpenAI a utilizar")
    temperature: float = Field(default=0.3, description="Temperatura para el LLM")


# ============================================================================
# MODELOS PYDANTIC DE ENTRADA
# ============================================================================

class Education(BaseModel):
    """Modelo de educación del candidato."""
    degree: str = Field(..., description="Título académico")
    name: str = Field(..., description="Nombre del programa")
    institute: str = Field(..., description="Institución educativa")
    start_date: str | None = Field(None, description="Fecha de inicio")
    end_date: str | None = Field(None, description="Fecha de finalización")


class Experience(BaseModel):
    """Modelo de experiencia laboral del candidato."""
    role: str = Field(..., description="Rol o puesto")
    company: str = Field(..., description="Empresa")
    description: str | None = Field(None, description="Descripción de responsabilidades")
    start_date: str | None = Field(None, description="Fecha de inicio")
    end_date: str | None = Field(None, description="Fecha de finalización")


class Language(BaseModel):
    """Modelo de idioma con nivel."""
    name: str = Field(..., description="Nombre del idioma")
    level: str | None = Field(None, description="Nivel de dominio")


class CandidateData(BaseModel):
    """Datos del candidato pre-procesados (candidateAdjusted)."""
    heading: str = Field(..., description="Resumen profesional del candidato")
    experience_years: int = Field(..., description="Años totales de experiencia")
    educations: list[Education] = Field(default_factory=list, description="Lista de educación")
    experiences: list[Experience] = Field(default_factory=list, description="Lista de experiencias laborales")
    skills: list[str] = Field(default_factory=list, description="Lista de habilidades técnicas")
    languages: list[Language] = Field(default_factory=list, description="Lista de idiomas con nivel")


class OfferData(BaseModel):
    """Datos de la oferta pre-procesados (offerAdjusted)."""
    job_title: str = Field(..., description="Título del puesto")
    company_name: str = Field(..., description="Nombre de la empresa")
    contract: str | None = Field(None, description="Tipo de contrato")
    type: Literal["remote", "on-site", "hybrid"] | None = Field(None, description="Modalidad de trabajo")
    description: str = Field(..., description="Descripción del puesto")
    salary_range: str | None = Field(None, description="Rango salarial")
    responsibilities: list[str] = Field(default_factory=list, description="Responsabilidades del puesto")
    experience_required: int | None = Field(None, description="Años de experiencia requeridos")
    mandatory_skills: list[str] = Field(default_factory=list, description="Habilidades obligatorias")
    nice_to_have_skills: list[str] = Field(default_factory=list, description="Habilidades deseables")
    mandatory_languages: list[str] = Field(default_factory=list, description="Idiomas obligatorios")
    nice_to_have_languages: list[str] = Field(default_factory=list, description="Idiomas deseables")
    preferred_companies: list[str] = Field(default_factory=list, description="Empresas preferidas")
    extra_requirements_to_consider: str | None = Field(None, description="Requisitos adicionales")


class EvaluationRequest(BaseModel):
    """Request del endpoint de evaluación."""
    offer: OfferData = Field(..., description="Datos de la oferta")
    candidate: CandidateData = Field(..., description="Datos del candidato")


# ============================================================================
# MODELOS PYDANTIC DE SALIDA (STRUCTURED OUTPUT)
# ============================================================================

class ScoreOutput(LangChainBaseModel):
    """Output estructurado de los agentes evaluadores."""
    score: int = Field(..., ge=0, le=100, description="Puntuación de 0 a 100")
    reason: str = Field(..., description="Justificación detallada de la puntuación")


class ScoringDecisionOutput(LangChainBaseModel):
    """Output del agente de scoring con decisión y compatibilidad."""
    compatibility_score: int = Field(..., ge=0, le=100, description="Puntuación de compatibilidad final ponderada")
    liked: bool = Field(..., description="Decisión binaria: true si compatibility >= 70")
    reasoning: str = Field(..., description="Razonamiento detrás de la decisión y ponderación")


class QAValidationOutput(LangChainBaseModel):
    """Output del agente de validación QA."""
    qa_required_human_review: bool = Field(..., description="Flag de revisión humana requerida")
    qa_note: str = Field(..., description="Nota o observación del QA")
    consistency_check: str = Field(..., description="Descripción de la verificación de coherencia")


# ============================================================================
# ESTADO DE LANGRAPH (TYPEDDICT)
# ============================================================================

class GraphState(TypedDict):
    """Estado del grafo de LangGraph."""
    offer: OfferData
    candidate: CandidateData
    technical_score: ScoreOutput | None
    trajectory_score: ScoreOutput | None
    cultural_score: ScoreOutput | None
    scoring_decision: ScoringDecisionOutput | None
    qa_validation: QAValidationOutput | None
    final_result: dict | None


# ============================================================================
# EXCEPCIONES PERSONALIZADAS
# ============================================================================

class EvaluationError(Exception):
    """Excepción base para errores de evaluación."""
    pass


class AgentExecutionError(EvaluationError):
    """Error en la ejecución de un agente."""
    pass


class InvalidInputError(EvaluationError):
    """Error en los datos de entrada."""
    pass


# ============================================================================
# AGENTES DE EVALUACIÓN
# ============================================================================

class AgentOrchestrator:
    """Orquestador de agentes con LLM configurado."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.temperature,
            api_key=settings.openai_api_key
        )
        self._setup_agents()
    
    def _setup_agents(self):
        """Configura los prompts de los agentes."""
        # Agente Técnico
        self.technical_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template("""
Eres un evaluador experto en habilidades técnicas para puestos de tecnología.

Tu tarea es evaluar ÚNICAMENTE la aptitud técnica del candidato comparando:
- Sus habilidades técnicas (skills) con las requeridas en la oferta (mandatory_skills, nice_to_have_skills)
- Sus idiomas (languages) con los requeridos (mandatory_languages, nice_to_have_languages)
- La experiencia técnica descrita en sus experiencias laborales

LIMITACIÓN ESTRICTA: No evalúes trayectoria profesional ni ajuste cultural. Solo aptitud técnica.

Evalúa en una escala de 0-100 donde:
- 0-30: Incompatibilidad técnica crítica (faltan habilidades obligatorias principales)
- 31-50: Compatibilidad técnica baja (faltan varias habilidades importantes)
- 51-70: Compatibilidad técnica moderada (cumple lo básico, faltan algunas habilidades deseables)
- 71-85: Compatibilidad técnica buena (cumple lo requerido y tiene algunas habilidades adicionales)
- 86-100: Compatibilidad técnica excelente (supera los requisitos técnicos)

Responde con un JSON estructurado con 'score' (int 0-100) y 'reason' (string detallado).
"""),
            HumanMessagePromptTemplate.from_template("""
OFERTA:
Título: {job_title}
Empresa: {company_name}
Descripción: {description}
Habilidades Obligatorias: {mandatory_skills}
Habilidades Deseables: {nice_to_have_skills}
Idiomas Obligatorios: {mandatory_languages}
Idiomas Deseables: {nice_to_have_languages}

CANDIDATO:
Resumen: {heading}
Años de Experiencia: {experience_years}
Habilidades: {skills}
Idiomas: {languages}
Experiencias Relevantes: {experiences_text}

Evalúa ÚNICAMENTE la aptitud técnica del candidato.
""")
        ])
        
        # Agente de Trayectoria
        self.trajectory_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template("""
Eres un evaluador experto en trayectorias profesionales y crecimiento de carrera.

Tu tarea es evaluar ÚNICAMENTE el ajuste de la trayectoria profesional del candidato con la oferta:
- Progresión de roles y responsabilidades
- Años de experiencia vs. requeridos
- Relevancia de experiencias previas con el rol ofertado
- Educación y formación relevante
- Empresas preferidas (si aplica)

LIMITACIÓN ESTRICTA: No evalúes habilidades técnicas específicas ni ajuste cultural. Solo trayectoria profesional.

Evalúa en una escala de 0-100 donde:
- 0-30: Trayectoria incompatible (sin experiencia relevante, sobre-calificado o sub-calificado extremo)
- 31-50: Trayectoria débilmente alineada (experiencia parcialmente relevante)
- 51-70: Trayectoria moderadamente alineada (experiencia relevante pero con gaps)
- 71-85: Trayectoria bien alineada (experiencia sólida y relevante)
- 86-100: Trayectoria excelentemente alineada (experiencia ideal y progresión clara)

Responde con un JSON estructurado con 'score' (int 0-100) y 'reason' (string detallado).
"""),
            HumanMessagePromptTemplate.from_template("""
OFERTA:
Título: {job_title}
Empresa: {company_name}
Años de Experiencia Requeridos: {experience_required}
Empresas Preferidas: {preferred_companies}
Descripción: {description}

CANDIDATO:
Resumen: {heading}
Años de Experiencia: {experience_years}
Educación: {educations_text}
Experiencias: {experiences_text}

Evalúa ÚNICAMENTE el ajuste de trayectoria profesional del candidato.
""")
        ])
        
        # Agente Cultural
        self.cultural_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template("""
Eres un evaluador experto en ajuste cultural y valores organizacionales.

Tu tarea es evaluar ÚNICAMENTE el ajuste cultural del candidato con la oferta:
- Modalidad de trabajo (remote/on-site/hybrid) vs. preferencias implícitas
- Tipo de contrato y flexibilidad
- Alineación con la cultura de la empresa (basado en descripción y requisitos adicionales)
- Valores y expectativas implícitas

LIMITACIÓN ESTRICTA: No evalúes habilidades técnicas ni trayectoria profesional. Solo ajuste cultural.

Evalúa en una escala de 0-100 donde:
- 0-30: Ajuste cultural muy bajo (conflictos evidentes en modalidad, valores, expectativas)
- 31-50: Ajuste cultural bajo (algunos desajustes importantes)
- 51-70: Ajuste cultural moderado (compatible pero con algunas diferencias)
- 71-85: Ajuste cultural bueno (bien alineado con la cultura)
- 86-100: Ajuste cultural excelente (perfectamente alineado)

Responde con un JSON estructurado con 'score' (int 0-100) y 'reason' (string detallado).
"""),
            HumanMessagePromptTemplate.from_template("""
OFERTA:
Empresa: {company_name}
Modalidad: {type}
Tipo de Contrato: {contract}
Descripción: {description}
Requisitos Adicionales: {extra_requirements}

CANDIDATO:
Resumen: {heading}
Experiencias: {experiences_text}

Evalúa ÚNICAMENTE el ajuste cultural del candidato.
""")
        ])
        
        # Agente de Scoring
        self.scoring_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template("""
Eres un agente de scoring especializado en tomar decisiones de contratación basadas en múltiples criterios.

Tu tarea es:
1. Ponderar las tres puntuaciones recibidas usando esta matriz:
   - Aptitud Técnica: 50% del peso
   - Ajuste de Trayectoria: 35% del peso
   - Ajuste Cultural: 15% del peso

2. Calcular la Puntuación de Compatibilidad Final usando la fórmula:
   Compatibilidad Final = (Técnica × 0.50) + (Trayectoria × 0.35) + (Cultural × 0.15)

3. Tomar la decisión binaria:
   - liked = true si Compatibilidad Final >= 70
   - liked = false si Compatibilidad Final < 70

4. Proporcionar un razonamiento claro que explique la ponderación y la decisión.

Responde con un JSON estructurado con 'compatibility_score' (int 0-100), 'liked' (bool), y 'reasoning' (string).
"""),
            HumanMessagePromptTemplate.from_template("""
PUNTUACIONES DE LOS EVALUADORES:

Técnica: {technical_score}/100
Razón Técnica: {technical_reason}

Trayectoria: {trajectory_score}/100
Razón Trayectoria: {trajectory_reason}

Cultural: {cultural_score}/100
Razón Cultural: {cultural_reason}

Calcula la Compatibilidad Final ponderada y toma la decisión binaria (liked/reject).
""")
        ])
        
        # Agente de Validación QA
        self.qa_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template("""
Eres un agente de Control de Calidad (QA) especializado en validar la coherencia de decisiones de evaluación.

Tu tarea es verificar si la decisión final es coherente con las puntuaciones individuales.

REGLAS DE INCONSISTENCIA CRÍTICA (marcar qa_required_human_review = true si se cumple ALGUNA):

1. La Puntuación de Compatibilidad Final es >= 70 (LIKED) pero la puntuación del Agente Técnico es < 50.
   → Esto indica que se aprobó a alguien con baja aptitud técnica, lo cual es riesgoso.

2. La Puntuación de Compatibilidad Final es < 70 (REJECTED) pero las tres puntuaciones individuales (Técnica, Trayectoria, Cultural) están todas por encima de 80.
   → Esto indica que se rechazó a alguien que tiene excelentes puntuaciones en todos los aspectos, lo cual es sospechoso.

Si NO se cumple ninguna de estas condiciones, marca qa_required_human_review = false y proporciona una nota de validación positiva.

Responde con un JSON estructurado con 'qa_required_human_review' (bool), 'qa_note' (string), y 'consistency_check' (string).
"""),
            HumanMessagePromptTemplate.from_template("""
RESULTADOS DE EVALUACIÓN:

Puntuación Técnica: {technical_score}/100
Puntuación Trayectoria: {trajectory_score}/100
Puntuación Cultural: {cultural_score}/100

Puntuación de Compatibilidad Final: {compatibility_score}/100
Decisión (liked): {liked}

Valida la coherencia de esta decisión según las reglas de inconsistencia crítica.
""")
        ])
    
    async def evaluate_technical(self, state: GraphState) -> GraphState:
        """Agente evaluador de habilidades técnicas."""
        try:
            offer = state["offer"]
            candidate = state["candidate"]
            
            # Preparar texto de experiencias
            experiences_text = "\n".join([
                f"- {exp.role} en {exp.company}: {exp.description or 'Sin descripción'}"
                for exp in candidate.experiences
            ]) or "Sin experiencias registradas"
            
            # Preparar prompt
            messages = self.technical_prompt.format_messages(
                job_title=offer.job_title,
                company_name=offer.company_name,
                description=offer.description,
                mandatory_skills=", ".join(offer.mandatory_skills) or "N/A",
                nice_to_have_skills=", ".join(offer.nice_to_have_skills) or "N/A",
                mandatory_languages=", ".join(offer.mandatory_languages) or "N/A",
                nice_to_have_languages=", ".join(offer.nice_to_have_languages) or "N/A",
                heading=candidate.heading,
                experience_years=candidate.experience_years,
                skills=", ".join(candidate.skills) or "N/A",
                languages=", ".join([f"{lang.name} ({lang.level or 'N/A'})" for lang in candidate.languages]) or "N/A",
                experiences_text=experiences_text
            )
            
            # LLM con structured output
            structured_llm = self.llm.with_structured_output(ScoreOutput)
            result = await structured_llm.ainvoke(messages)
            
            state["technical_score"] = result
            logger.info(f"Technical Score: {result.score}/100")
            return state
            
        except Exception as e:
            logger.error(f"Error en evaluación técnica: {e}", exc_info=True)
            raise AgentExecutionError(f"Error en agente técnico: {str(e)}")
    
    async def evaluate_trajectory(self, state: GraphState) -> GraphState:
        """Agente evaluador de trayectoria profesional."""
        try:
            offer = state["offer"]
            candidate = state["candidate"]
            
            # Preparar textos
            educations_text = "\n".join([
                f"- {edu.degree} en {edu.name} ({edu.institute})"
                for edu in candidate.educations
            ]) or "Sin educación registrada"
            
            experiences_text = "\n".join([
                f"- {exp.role} en {exp.company} ({exp.start_date or 'N/A'} - {exp.end_date or 'Actual'}): {exp.description or 'Sin descripción'}"
                for exp in candidate.experiences
            ]) or "Sin experiencias registradas"
            
            messages = self.trajectory_prompt.format_messages(
                job_title=offer.job_title,
                company_name=offer.company_name,
                experience_required=str(offer.experience_required) if offer.experience_required else "N/A",
                preferred_companies=", ".join(offer.preferred_companies) or "N/A",
                description=offer.description,
                heading=candidate.heading,
                experience_years=candidate.experience_years,
                educations_text=educations_text,
                experiences_text=experiences_text
            )
            
            structured_llm = self.llm.with_structured_output(ScoreOutput)
            result = await structured_llm.ainvoke(messages)
            
            state["trajectory_score"] = result
            logger.info(f"Trajectory Score: {result.score}/100")
            return state
            
        except Exception as e:
            logger.error(f"Error en evaluación de trayectoria: {e}", exc_info=True)
            raise AgentExecutionError(f"Error en agente de trayectoria: {str(e)}")
    
    async def evaluate_cultural(self, state: GraphState) -> GraphState:
        """Agente evaluador de ajuste cultural."""
        try:
            offer = state["offer"]
            candidate = state["candidate"]
            
            experiences_text = "\n".join([
                f"- {exp.role} en {exp.company}: {exp.description or 'Sin descripción'}"
                for exp in candidate.experiences
            ]) or "Sin experiencias registradas"
            
            messages = self.cultural_prompt.format_messages(
                company_name=offer.company_name,
                type=offer.type or "N/A",
                contract=offer.contract or "N/A",
                description=offer.description,
                extra_requirements=offer.extra_requirements_to_consider or "N/A",
                heading=candidate.heading,
                experiences_text=experiences_text
            )
            
            structured_llm = self.llm.with_structured_output(ScoreOutput)
            result = await structured_llm.ainvoke(messages)
            
            state["cultural_score"] = result
            logger.info(f"Cultural Score: {result.score}/100")
            return state
            
        except Exception as e:
            logger.error(f"Error en evaluación cultural: {e}", exc_info=True)
            raise AgentExecutionError(f"Error en agente cultural: {str(e)}")
    
    async def scoring_decision(self, state: GraphState) -> GraphState:
        """Agente de scoring que toma la decisión final."""
        try:
            technical = state["technical_score"]
            trajectory = state["trajectory_score"]
            cultural = state["cultural_score"]
            
            if not all([technical, trajectory, cultural]):
                raise AgentExecutionError("Faltan puntuaciones de los evaluadores")
            
            messages = self.scoring_prompt.format_messages(
                technical_score=technical.score,
                technical_reason=technical.reason,
                trajectory_score=trajectory.score,
                trajectory_reason=trajectory.reason,
                cultural_score=cultural.score,
                cultural_reason=cultural.reason
            )
            
            structured_llm = self.llm.with_structured_output(ScoringDecisionOutput)
            result = await structured_llm.ainvoke(messages)
            
            state["scoring_decision"] = result
            logger.info(f"Scoring Decision: Compatibility={result.compatibility_score}, Liked={result.liked}")
            return state
            
        except Exception as e:
            logger.error(f"Error en scoring: {e}", exc_info=True)
            raise AgentExecutionError(f"Error en agente de scoring: {str(e)}")
    
    async def qa_validation(self, state: GraphState) -> GraphState:
        """Agente de validación QA."""
        try:
            technical = state["technical_score"]
            trajectory = state["trajectory_score"]
            cultural = state["cultural_score"]
            scoring = state["scoring_decision"]
            
            if not all([technical, trajectory, cultural, scoring]):
                raise AgentExecutionError("Faltan datos para validación QA")
            
            messages = self.qa_prompt.format_messages(
                technical_score=technical.score,
                trajectory_score=trajectory.score,
                cultural_score=cultural.score,
                compatibility_score=scoring.compatibility_score,
                liked=str(scoring.liked).lower()
            )
            
            structured_llm = self.llm.with_structured_output(QAValidationOutput)
            result = await structured_llm.ainvoke(messages)
            
            state["qa_validation"] = result
            logger.info(f"QA Validation: Human Review Required={result.qa_required_human_review}")
            return state
            
        except Exception as e:
            logger.error(f"Error en QA: {e}", exc_info=True)
            raise AgentExecutionError(f"Error en agente QA: {str(e)}")
    
    def finalize_result(self, state: GraphState) -> GraphState:
        """Finaliza y estructura el resultado final."""
        try:
            technical = state["technical_score"]
            trajectory = state["trajectory_score"]
            cultural = state["cultural_score"]
            scoring = state["scoring_decision"]
            qa = state["qa_validation"]
            
            # Construir razones
            ai_swipe_reasons = [
                f"Técnica ({technical.score}/100): {technical.reason}",
                f"Trayectoria ({trajectory.score}/100): {trajectory.reason}",
                f"Cultural ({cultural.score}/100): {cultural.reason}",
                f"QA: {qa.qa_note}"
            ]
            
            # Priorizar nota de QA en la razón final si existe
            final_reason = qa.qa_note if qa.qa_required_human_review else scoring.reasoning
            
            result = {
                "liked": scoring.liked,
                "reason": final_reason,
                "compatibility": scoring.compatibility_score,
                "ai_swipe_reasons": ai_swipe_reasons,
                "models_liked": 5 if scoring.liked else 0,
                "models_evaluated": 5,
                "qa_required_human_review": qa.qa_required_human_review
            }
            
            state["final_result"] = result
            logger.info(f"Final Result: Liked={result['liked']}, Compatibility={result['compatibility']}")
            return state
            
        except Exception as e:
            logger.error(f"Error al finalizar resultado: {e}", exc_info=True)
            raise AgentExecutionError(f"Error al finalizar resultado: {str(e)}")


# ============================================================================
# CONSTRUCCIÓN DEL GRAFO LANGRAPH
# ============================================================================

def build_evaluation_graph(agent_orchestrator: AgentOrchestrator) -> StateGraph:
    """Construye el grafo de LangGraph para la evaluación."""
    
    async def parallel_evaluation(state: GraphState) -> GraphState:
        """
        Nodo que ejecuta los tres evaluadores en paralelo usando asyncio.gather.
        Esto garantiza ejecución paralela real de los agentes.
        """
        # Ejecutar los tres evaluadores en paralelo
        technical_state, trajectory_state, cultural_state = await asyncio.gather(
            agent_orchestrator.evaluate_technical(state),
            agent_orchestrator.evaluate_trajectory(state),
            agent_orchestrator.evaluate_cultural(state)
        )
        
        # Combinar los resultados en un solo estado
        # Construir el estado final con todos los scores
        final_state: GraphState = {
            "offer": state["offer"],
            "candidate": state["candidate"],
            "technical_score": technical_state.get("technical_score"),
            "trajectory_score": trajectory_state.get("trajectory_score"),
            "cultural_score": cultural_state.get("cultural_score"),
            "scoring_decision": None,
            "qa_validation": None,
            "final_result": None
        }
        
        return final_state
    
    workflow = StateGraph(GraphState)
    
    # Agregar nodos
    workflow.add_node("parallel_evaluation", parallel_evaluation)
    workflow.add_node("scoring", agent_orchestrator.scoring_decision)
    workflow.add_node("qa_validation", agent_orchestrator.qa_validation)
    workflow.add_node("finalize", agent_orchestrator.finalize_result)
    
    # Establecer punto de entrada
    workflow.set_entry_point("parallel_evaluation")
    
    # Flujo secuencial después de la evaluación paralela
    workflow.add_edge("parallel_evaluation", "scoring")
    workflow.add_edge("scoring", "qa_validation")
    workflow.add_edge("qa_validation", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile(checkpointer=MemorySaver())


# ============================================================================
# MODELO PYDANTIC DE RESPUESTA FINAL
# ============================================================================

class EvaluationResult(BaseModel):
    """Resultado final de la evaluación."""
    liked: bool = Field(..., description="Decisión binaria: true si el candidato es compatible")
    reason: str = Field(..., description="Justificación final de la decisión")
    compatibility: int = Field(..., ge=0, le=100, description="Puntuación de compatibilidad final (0-100)")
    ai_swipe_reasons: list[str] = Field(..., description="Razones detalladas de cada agente")
    models_liked: int = Field(..., description="Número de modelos que votaron por liked")
    models_evaluated: int = Field(..., description="Número total de modelos evaluados")
    qa_required_human_review: bool = Field(..., description="Flag que indica si se requiere revisión humana")


# ============================================================================
# FASTAPI APP Y ENDPOINTS
# ============================================================================

app = FastAPI(
    title="MAS-Eval: Microservicio Multiagente de Evaluación de Candidatos",
    description="Servicio de evaluación de candidatos utilizando LangGraph con 5 agentes especializados",
    version="1.0.0"
)


def get_settings() -> Settings:
    """Dependency para obtener configuración."""
    return Settings()


def get_agent_orchestrator(settings: Settings = Depends(get_settings)) -> AgentOrchestrator:
    """Dependency para obtener el orquestador de agentes."""
    return AgentOrchestrator(settings)


def get_evaluation_graph(
    agent_orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator)
) -> StateGraph:
    """Dependency para obtener el grafo de evaluación."""
    return build_evaluation_graph(agent_orchestrator)


@app.get("/health")
async def health_check():
    """Endpoint de health check."""
    return {"status": "healthy", "service": "MAS-Eval"}


@app.post("/evaluate", response_model=EvaluationResult)
async def evaluate_candidate(
    request: EvaluationRequest,
    graph: StateGraph = Depends(get_evaluation_graph)
):
    """
    Endpoint principal de evaluación de candidatos.
    
    Recibe los datos de la oferta y el candidato pre-procesados y retorna
    una evaluación completa con decisión de swipe (liked/reject), score
    de compatibilidad y justificación detallada.
    """
    try:
        # Validar entrada
        if not request.offer or not request.candidate:
            raise InvalidInputError("Los datos de oferta y candidato son requeridos")
        
        # Inicializar estado
        initial_state: GraphState = {
            "offer": request.offer,
            "candidate": request.candidate,
            "technical_score": None,
            "trajectory_score": None,
            "cultural_score": None,
            "scoring_decision": None,
            "qa_validation": None,
            "final_result": None
        }
        
        # Ejecutar grafo
        config = {"configurable": {"thread_id": "evaluation-1"}}
        final_state = await graph.ainvoke(initial_state, config)
        
        # Validar resultado
        if not final_state.get("final_result"):
            raise EvaluationError("El grafo no produjo un resultado final")
        
        result_data = final_state["final_result"]
        result = EvaluationResult(**result_data)
        
        logger.info(f"Evaluation completed: Liked={result.liked}, Compatibility={result.compatibility}")
        return result
        
    except InvalidInputError as e:
        logger.warning(f"Invalid input: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except AgentExecutionError as e:
        logger.error(f"Agent execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Error en ejecución de agente: {str(e)}")
    except EvaluationError as e:
        logger.error(f"Evaluation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")


# ============================================================================
# MOCKS DE DATOS Y PRUEBA DE EJECUCIÓN
# ============================================================================

def create_mock_offer() -> OfferData:
    """Crea datos mock de una oferta de alta fidelidad."""
    return OfferData(
        job_title="Senior Python Engineer",
        company_name="TechCorp Innovations",
        contract="Indefinido",
        type="hybrid",
        description="Buscamos un ingeniero senior de Python con experiencia en microservicios y arquitecturas distribuidas. El candidato trabajará en un equipo ágil desarrollando APIs RESTful y servicios cloud-native.",
        salary_range="€50,000 - €70,000",
        responsibilities=[
            "Desarrollar y mantener microservicios en Python",
            "Diseñar APIs RESTful",
            "Colaborar con equipos cross-functional",
            "Implementar mejores prácticas de código limpio"
        ],
        experience_required=5,
        mandatory_skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
        nice_to_have_skills=["LangGraph", "LangChain", "Google Cloud", "Kubernetes"],
        mandatory_languages=["English", "Spanish"],
        nice_to_have_languages=["French"],
        preferred_companies=["Google", "Microsoft", "Amazon"],
        extra_requirements_to_consider="Experiencia previa en startups de tecnología y capacidad de trabajo en equipo remoto."
    )


def create_mock_candidate() -> CandidateData:
    """Crea datos mock de un candidato de alta fidelidad."""
    return CandidateData(
        heading="Ingeniero de Software con 8 años de experiencia en desarrollo backend, especializado en Python y arquitecturas microservicios.",
        experience_years=8,
        educations=[
            Education(
                degree="Grado en Ingeniería Informática",
                name="Ingeniería de Software",
                institute="Universidad Tecnológica",
                start_date="2010",
                end_date="2014"
            )
        ],
        experiences=[
            Experience(
                role="Senior Backend Engineer",
                company="StartupTech",
                description="Desarrollo de microservicios en Python usando FastAPI y Docker. Lideré la migración de monolitos a arquitectura de microservicios.",
                start_date="2020-01",
                end_date="2024-12"
            ),
            Experience(
                role="Backend Developer",
                company="WebSolutions",
                description="Desarrollo de APIs RESTful y mantenimiento de bases de datos PostgreSQL. Trabajé en un equipo ágil de 8 personas.",
                start_date="2016-06",
                end_date="2019-12"
            )
        ],
        skills=["Python", "FastAPI", "Docker", "PostgreSQL", "LangGraph", "LangChain", "AWS"],
        languages=[
            Language(name="Spanish", level="Native"),
            Language(name="English", level="Fluent"),
            Language(name="French", level="Intermediate")
        ]
    )


async def test_graph_execution():
    """Función de prueba que ejecuta el grafo con datos mock."""
    logger.info("=" * 80)
    logger.info("🧪 INICIANDO PRUEBA DE EJECUCIÓN DEL GRAFO CON DATOS MOCK")
    logger.info("=" * 80)
    
    try:
        # Crear configuración de prueba
        # Intentar cargar desde entorno, si no existe usar una clave de prueba (fallará en llamadas reales)
        try:
            settings = Settings()
        except Exception:
            # Si no hay configuración en entorno, crear una con clave de prueba
            # Nota: Esto causará error al hacer llamadas reales a OpenAI
            logger.warning("No se encontró OPENAI_API_KEY en entorno. Usando clave de prueba (las llamadas fallarán).")
            settings = Settings(openai_api_key="test-key-for-mock")
        
        # Crear orquestador y grafo
        logger.info("📦 Creando orquestador de agentes...")
        agent_orchestrator = AgentOrchestrator(settings)
        graph = build_evaluation_graph(agent_orchestrator)
        
        # Crear datos mock
        logger.info("📝 Creando datos mock de oferta y candidato...")
        mock_offer = create_mock_offer()
        mock_candidate = create_mock_candidate()
        
        # Inicializar estado
        initial_state: GraphState = {
            "offer": mock_offer,
            "candidate": mock_candidate,
            "technical_score": None,
            "trajectory_score": None,
            "cultural_score": None,
            "scoring_decision": None,
            "qa_validation": None,
            "final_result": None
        }
        
        logger.info("🚀 Ejecutando grafo de evaluación...")
        logger.info(f"   Oferta: {mock_offer.job_title} en {mock_offer.company_name}")
        logger.info(f"   Candidato: {mock_candidate.heading[:60]}...")
        
        # Ejecutar grafo
        config = {"configurable": {"thread_id": "test-execution-1"}}
        final_state = await graph.ainvoke(initial_state, config)
        
        # Mostrar resultados
        logger.info("=" * 80)
        logger.info("✅ RESULTADOS DE LA EVALUACIÓN")
        logger.info("=" * 80)
        
        if final_state.get("final_result"):
            result = final_state["final_result"]
            logger.info(f"📊 Decisión Final: {'✅ LIKED' if result['liked'] else '❌ REJECTED'}")
            logger.info(f"📈 Compatibilidad: {result['compatibility']}/100")
            logger.info(f"🔍 Revisión Humana Requerida: {'⚠️ SÍ' if result['qa_required_human_review'] else '✅ NO'}")
            logger.info(f"\n💬 Razón Final:\n{result['reason']}\n")
            logger.info("📋 Razones Detalladas por Agente:")
            for i, reason in enumerate(result['ai_swipe_reasons'], 1):
                logger.info(f"   {i}. {reason}")
        else:
            logger.error("❌ El grafo no produjo un resultado final")
        
        logger.info("=" * 80)
        logger.info("✅ PRUEBA COMPLETADA EXITOSAMENTE")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Error en la prueba: {e}", exc_info=True)
        raise


# ============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Ejecutar prueba del grafo antes de iniciar el servidor
    logger.info("Iniciando prueba de ejecución del grafo...")
    asyncio.run(test_graph_execution())
    
    # Iniciar servidor FastAPI
    logger.info("Iniciando servidor FastAPI en http://0.0.0.0:8080")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=False
    )
