# 📁 Refactoring Guide - Clean Code Architecture

## 🎯 Overview

The codebase has been completely refactored following clean code principles and best practices. The monolithic `main.py` file has been split into a modular, maintainable architecture.

## 📂 New Project Structure

```
test-evaluate-agents/
├── src/                          # Main source code
│   ├── __init__.py
│   ├── exceptions.py             # Custom exceptions
│   │
│   ├── config/                   # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py           # Settings with pydantic-settings
│   │
│   ├── models/                   # Pydantic data models
│   │   ├── __init__.py
│   │   ├── requests.py           # Request models (Offer, Candidate, etc.)
│   │   ├── responses.py          # Response models (Results, Scores, etc.)
│   │   └── state.py              # LangGraph state model
│   │
│   ├── agents/                   # AI Agents
│   │   ├── __init__.py
│   │   ├── factory.py            # Agent factory orchestrator
│   │   ├── technical_skills.py   # Technical evaluator (50% weight)
│   │   ├── career_trajectory.py  # Career evaluator (35% weight)
│   │   ├── cultural_fit.py       # Culture evaluator (15% weight)
│   │   ├── scoring.py            # Scoring & decision agent
│   │   └── qa_validation.py      # QA validation agent
│   │
│   ├── graph/                    # LangGraph workflow
│   │   ├── __init__.py
│   │   └── builder.py            # Graph builder
│   │
│   ├── services/                 # Business logic services
│   │   ├── __init__.py
│   │   ├── evaluation.py         # Evaluation orchestration
│   │   └── logging.py            # Result logging to JSON
│   │
│   └── api/                      # FastAPI application
│       ├── __init__.py
│       ├── dependencies.py       # Dependency injection container
│       └── routes.py             # API routes and endpoints
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── test_data.py              # Mock data (good & bad candidates)
│   └── test_workflow.py          # Integration tests
│
├── main.py                       # Simple entry point
├── main_old.py                   # Backup of original monolithic file
├── requirements.txt
├── .env
└── evaluation_results/           # Saved evaluation logs (gitignored)
```

## 🏗️ Architecture Principles

### 1. **Separation of Concerns**
Each module has a single, well-defined responsibility:
- **models/**: Data structures only
- **agents/**: Agent logic only
- **services/**: Business orchestration
- **api/**: HTTP layer only

### 2. **Dependency Injection**
- Container pattern in `api/dependencies.py`
- Easy testing and mocking
- Clear dependency graph

### 3. **Single Responsibility Principle**
- Each agent in its own file
- Each model category separated
- Services focused on single tasks

### 4. **Interface Segregation**
- Clean imports via `__init__.py` files
- Explicit exports with `__all__`

### 5. **DRY (Don't Repeat Yourself)**
- Reusable `AgentFactory._execute_agent()` method
- Centralized logging and error handling

## 🚀 Usage

### Run Tests and Server
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\Activate.ps1  # Windows PowerShell

# Run tests then start server
python main.py
```

### Run Tests Only
```bash
python main.py --test
```

### Run Server Only
```python
from src.api import create_app
import uvicorn

app = create_app()
uvicorn.run(app, host="0.0.0.0", port=8080)
```

### Use as Library
```python
from src.config import get_settings, setup_logging
from src.api.dependencies import get_container

# Setup
settings = get_settings()
setup_logging(settings)

# Initialize dependencies
container = get_container()
await container.initialize(settings)

# Use evaluation service
from tests import create_mock_good_candidate
request = create_mock_good_candidate()
result = await container.evaluation_service.evaluate(request)
```

## 📊 Module Breakdown

### Configuration (`src/config/`)
- **settings.py**: Environment variable management with pydantic-settings
- Centralized logging setup
- Cached settings singleton

### Models (`src/models/`)
- **requests.py**: Input models (OfferData, CandidateData, etc.)
- **responses.py**: Output models (EvaluationResult, ScoreOutput, etc.)
- **state.py**: LangGraph state management

### Agents (`src/agents/`)
- **factory.py**: Orchestrates all agents, provides execution framework
- **technical_skills.py**: 50% weight - Technical competency evaluation
- **career_trajectory.py**: 35% weight - Career progression evaluation
- **cultural_fit.py**: 15% weight - Culture & work style evaluation
- **scoring.py**: Weighted score calculation & binary decision
- **qa_validation.py**: Consistency checks & human review flagging

### Graph (`src/graph/`)
- **builder.py**: LangGraph workflow construction
- Sequential agent execution pipeline
- State management and checkpointing

### Services (`src/services/`)
- **evaluation.py**: Main evaluation orchestration service
- **logging.py**: JSON result persistence with timestamps

### API (`src/api/`)
- **dependencies.py**: Dependency injection container
- **routes.py**: FastAPI app creation, endpoints, error handling

### Tests (`tests/`)
- **test_data.py**: Mock candidates (good & bad scenarios)
- **test_workflow.py**: End-to-end workflow testing

## 🔧 Benefits of Refactoring

### ✅ Maintainability
- Easy to locate and fix bugs
- Clear module boundaries
- Self-documenting structure

### ✅ Testability
- Each component can be tested in isolation
- Easy to mock dependencies
- Clear integration points

### ✅ Scalability
- Easy to add new agents
- Simple to extend functionality
- Modular architecture supports growth

### ✅ Readability
- Small, focused files
- Clear naming conventions
- Logical organization

### ✅ Reusability
- Agents can be used independently
- Services can be imported as library
- Models shared across modules

## 📝 Adding New Features

### Adding a New Agent
1. Create `src/agents/new_agent.py`
2. Implement with `evaluate(state, executor)` method
3. Add to `AgentFactory` in `factory.py`
4. Update `GraphBuilder` to include in workflow

### Adding a New Endpoint
1. Add route function in `src/api/routes.py`
2. Use dependency injection for services
3. Define request/response models in `src/models/`

### Adding New Models
1. Add to appropriate file in `src/models/`
2. Export in `src/models/__init__.py`
3. Use across the application

## 🎓 Code Quality Standards

- ✅ PEP 8 compliant
- ✅ Type hints throughout
- ✅ Docstrings for all public methods
- ✅ Logging at appropriate levels
- ✅ Exception handling with custom exceptions
- ✅ No circular dependencies

## 📚 Migration from Old Code

The original monolithic `main.py` has been preserved as `main_old.py` for reference. All functionality has been preserved and enhanced in the new structure.

### Key Changes
- **1268 lines** → **Modular 100-200 line files**
- **1 file** → **20+ focused modules**
- **Monolithic** → **Clean Architecture**

## 🔍 Testing Results

```
TEST CASE 1: GOOD CANDIDATE → ✅ LIKED (Score: 88/100)
TEST CASE 2: BAD CANDIDATE  → ❌ REJECTED (Score: 10/100)
```

Both test cases pass successfully with proper evaluation and JSON logging.

---

**Refactored by:** AI Assistant  
**Date:** November 2025  
**Principle:** Clean Code, SOLID, DRY

