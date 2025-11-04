# Sistema de Logs de Evaluación

## Descripción

El sistema MAS-Eval ahora incluye un sistema automático de guardado de resultados de evaluaciones en archivos JSON estructurados con timestamps.

## Características

### 📁 Almacenamiento Automático

Cada evaluación se guarda automáticamente en el directorio `evaluation_results/` con el siguiente formato de nombre:
```
{test_name}_{timestamp}.json
```

Ejemplo:
- `good_candidate_20251104_152658.json`
- `bad_candidate_20251104_152714.json`

### 📋 Estructura del Log JSON

Cada archivo contiene:

```json
{
  "test_name": "nombre_del_test",
  "timestamp": "2025-11-04T15:27:14.226902",
  "request": {
    "offer": {
      "job_title": "...",
      "company_name": "...",
      "mandatory_skills": [...],
      "nice_to_have_skills": [...],
      "mandatory_languages": [...]
    },
    "candidate": {
      "heading": "...",
      "experience_years": 0,
      "skills": [...],
      "languages": [...],
      "experience_summary": [...]
    }
  },
  "result": {
    "liked": true/false,
    "compatibility_score": 0-100,
    "qa_required_human_review": true/false,
    "final_reason": "...",
    "models_liked": 5,
    "models_evaluated": 5,
    "detailed_evaluations": [
      "Technical Skills (X/100): ...",
      "Career Trajectory (X/100): ...",
      "Cultural Fit (X/100): ...",
      "QA Validation: ..."
    ]
  }
}
```

## Casos de Prueba

### ✅ Test Case 1: Good Candidate (LIKED)

**Perfil:**
- Senior Full-Stack Engineer con 7 años de experiencia
- Dominio experto de Python, React, AWS, Docker
- Experiencia liderando equipos y proyectos cloud

**Resultado Esperado:**
- Score: 85-95/100
- Decisión: LIKED ❤️

**Puntuaciones típicas:**
- Technical Skills: 90/100
- Career Trajectory: 90/100
- Cultural Fit: 85/100
- **Final Score: 88/100**

---

### ❌ Test Case 2: Bad Candidate (REJECTED)

**Perfil:**
- Junior PHP Developer con 2 años de experiencia
- Especialista en WordPress
- Sin experiencia en tecnologías modernas (React, AWS, Docker)
- Idiomas: Solo inglés intermedio (falta español)

**Resultado Esperado:**
- Score: 20-35/100
- Decisión: REJECTED ❌

**Puntuaciones típicas:**
- Technical Skills: 20/100
- Career Trajectory: 30/100
- Cultural Fit: 30/100
- **Final Score: 25/100**

## Uso

### Ejecutar Tests con Guardado Automático

```bash
# Activar entorno virtual
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\Activate.ps1  # Windows PowerShell

# Ejecutar tests
python main.py
```

### Resultados

Los logs se guardan automáticamente en:
```
evaluation_results/
├── good_candidate_20251104_152658.json
└── bad_candidate_20251104_152714.json
```

### Consultar Resultados

```bash
# Ver todos los resultados
ls evaluation_results/

# Leer un resultado específico
cat evaluation_results/good_candidate_*.json | jq '.'
```

## Integración con API

La función `save_evaluation_result()` también puede ser utilizada en el endpoint `/evaluate` de FastAPI para guardar automáticamente todas las evaluaciones en producción.

### Ejemplo de Integración

```python
@app.post("/evaluate", response_model=EvaluationResult)
async def evaluate_candidate(
    request: EvaluationRequest,
    service: EvaluationService = Depends(get_evaluation_service)
) -> EvaluationResult:
    result = await service.evaluate(request)
    
    # Guardar resultado para auditoría
    save_evaluation_result(request, result, f"api_request_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    return result
```

## Ventajas

✅ **Trazabilidad**: Historial completo de todas las evaluaciones  
✅ **Auditoría**: Revisión de decisiones pasadas del sistema  
✅ **Análisis**: Datos estructurados para análisis de rendimiento  
✅ **Debug**: Facilita la depuración de casos edge  
✅ **Compliance**: Cumplimiento con requisitos de documentación

## Notas

- Los archivos JSON están formateados con indentación para fácil lectura humana
- Se usa `ensure_ascii=False` para preservar caracteres especiales (ñ, acentos, etc.)
- El directorio `evaluation_results/` está excluido del control de versiones (`.gitignore`)
- Cada evaluación incluye timestamp ISO 8601 para ordenamiento cronológico preciso

