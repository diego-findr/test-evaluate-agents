# 🚀 MAS-Eval: Microservicio Multiagente de Evaluación de Candidatos

## 💡 Visión General del Proyecto

**MAS-Eval** (Multi-Agent Swiping & Evaluation) es un microservicio de alta precisión diseñado para reemplazar la lógica de evaluación de candidatos en el backend de Supabase. Utiliza una arquitectura de **cinco (5) Agentes de IA** orquestados por **LangGraph** para realizar una evaluación holística (Técnica, Trayectoria, Cultural, Scoring y QA), garantizando una decisión de *swipe* más precisa y justificable.

El servicio está construido con **Python 3.11**, **FastAPI** y sigue los estándares de **Clean Code / Senior A++** para ser desplegado en **Google Cloud Run**.

---

## 🏗️ Arquitectura y Componentes Clave

### 1. El Grafo (LangGraph)

El flujo de evaluación se divide en tres fases principales utilizando **Nodos Paralelos** y **Aristas Condicionales**:

| Fase | Nodos/Agentes Involucrados | Tipo de Ejecución | Objetivo |
| :--- | :--- | :--- | :--- |
| **Evaluación Paralela** | Technical, Trajectory, Cultural | **Paralelo** | Generar las 3 puntuaciones primarias y sus razones. |
| **Decisión & Scoring** | Agente de Scoring | Secuencial | Ponderar las puntuaciones y emitir la Decisión Inicial (`liked`). |
| **Validación de Calidad (QA)** | Agente de Validación (QA) | Secuencial / Condicional | Revisar la coherencia de la decisión inicial y emitir el *flag* `qa_required_human_review`. |

### 2. Lógica de Decisión Explícita

* **Ponderación del Scoring:** El Agente de Scoring aplica los siguientes pesos:
    * **Aptitud Técnica:** 50%
    * **Ajuste de Trayectoria:** 35%
    * **Ajuste Cultural:** 15%
* **Regla Binaria:** `liked = true` si `Final Compatibility Score >= 70`.
* **Regla de QA Crítica:** `qa_required_human_review = true` si hay incoherencia (ej., LIKED pero Técnica < 50, o REJECTED pero los tres scores están por encima de 80).

### 3. Contrato de Datos (Pydantic)

El código utiliza modelos Pydantic estrictos, incluyendo `OfferData` y `CandidateData` para la entrada, y `EvaluationResult` para la salida.

---

## ⚙️ Configuración y Despliegue

### 1. Requisitos de Entorno

* **Python:** 3.11+
* **Frameworks:** `fastapi`, `langchain`, `langgraph`, `pydantic`, `pydantic-settings`.

### 2. Variables de Entorno

El servicio utiliza `pydantic-settings` para cargar la clave del LLM de manera tipada y segura.

| Variable | Descripción |
| :--- | :--- |
| `OPENAI_API_KEY` | Clave de acceso para el modelo de OpenAI. |

### 3. Despliegue en Cloud Run

1.  Asegúrate de tener un **`Dockerfile`** simple que exponga el puerto 8080.
2.  Construye y despliega la imagen en tu proyecto de Google Cloud, asegurando que la variable `OPENAI_API_KEY` esté configurada.

---

## 💻 Integración y Uso del API

El microservicio expone un único *endpoint* asíncrono para la evaluación.

### Endpoint: `/evaluate`

* **Método:** `POST`
* **Cuerpo de la Petición (JSON):** Debe contener los objetos `offer` (`OfferData`) y `candidate` (`CandidateData`) en el formato pre-procesado por el controlador de Supabase (`offerAdjusted` y `candidateAdjusted`).

    ```json
    {
      "offer": { "job_title": "Senior Engineer...", "mandatory_skills": ["Python", "LangGraph"] },
      "candidate": { "heading": "Software Developer...", "experience_years": 8 }
    }
    ```

* **Respuesta Exitosa (200 OK):**
    El JSON de salida (`EvaluationResult`) es directamente consumible por la lógica de Supabase:

    ```json
    {
      "liked": true,
      "reason": "La aptitud técnica alta compensó el riesgo de trayectoria. QA validó la coherencia.",
      "compatibility": 81,
      "ai_swipe_reasons": ["Técnica: 90/100...", "Trayectoria: 70/100...", "Cultural: 75/100...", "QA: OK. Coherencia validada."],
      "models_liked": 5,
      "models_evaluated": 5,
      "qa_required_human_review": false
    }
    ```

---

## 🧪 Pruebas y Desarrollo

Para un desarrollo Senior A++:

* **Mocks de Datos:** El archivo `main.py` incluye **Mocks de Datos de Entrada** de alta fidelidad.
* **Prueba de Grafo:** El bloque `if __name__ == "__main__":` ejecuta una función asíncrona de prueba (`test_graph_execution`) que valida el flujo de LangGraph con los mocks antes de iniciar el servidor de FastAPI.
