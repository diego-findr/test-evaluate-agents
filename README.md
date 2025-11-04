# MAS-Eval: Multi-Agent System for Candidate Evaluation

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Code Style](https://img.shields.io/badge/code%20style-clean-brightgreen.svg)]()

> Production-grade AI-powered candidate evaluation microservice using LangGraph multi-agent orchestration

## 🎯 Overview

MAS-Eval is a sophisticated multi-agent system that evaluates candidate-job compatibility using specialized AI agents. Built with LangGraph, FastAPI, and OpenAI GPT-4o-mini, it provides comprehensive, explainable evaluations across technical skills, career trajectory, and cultural fit.

### Key Features

- **🤖 5 Specialized AI Agents**: Technical Skills, Career Trajectory, Cultural Fit, Scoring, and QA Validation
- **⚖️ Weighted Scoring System**: Technical (50%), Career (35%), Cultural (15%)
- **🔍 QA Validation**: Automatic inconsistency detection and human review flagging
- **📊 Comprehensive Logging**: JSON-based evaluation history with timestamps
- **🚀 REST API**: FastAPI-powered endpoints with automatic documentation
- **🏗️ Clean Architecture**: Modular, testable, and maintainable codebase

## 🏆 Architecture Highlights

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI REST API                          │
│                  (Dependency Injection)                      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Evaluation Service                          │
│              (Orchestration & Results)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  LangGraph Workflow                          │
│           (State Management & Checkpointing)                 │
└────┬───────┬──────────┬──────────┬───────────┬──────────────┘
     │       │          │          │           │
┌────▼──┐ ┌─▼────┐ ┌──▼─────┐ ┌──▼──────┐ ┌─▼──────────┐
│ Tech  │ │Career│ │Cultural│ │ Scoring │ │ QA         │
│ Skills│ │ Traj.│ │  Fit   │ │ Agent   │ │ Validation │
│ 50%   │ │ 35%  │ │  15%   │ │ Weighted│ │ Consistency│
└───────┘ └──────┘ └────────┘ └─────────┘ └────────────┘
```

## 📦 Installation

### Prerequisites

- Python 3.11+
- OpenAI API Key

### Setup

```bash
# Clone repository
git clone <repository-url>
cd test-evaluate-agents

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

## 🚀 Quick Start

### Run Tests and Server

```bash
python main.py
```

This will:
1. Run integration tests with good and bad candidate scenarios
2. Save results to `evaluation_results/`
3. Start the FastAPI server on `http://localhost:8080`

### Run Tests Only

```bash
python main.py --test
```

### Access API Documentation

Once the server is running:
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

## 📖 Usage

### API Endpoint

**POST** `/evaluate`

**Request Body:**
```json
{
  "offer": {
    "job_title": "Senior Full-Stack Developer",
    "company_name": "TechCorp",
    "mandatory_skills": ["Python", "React", "AWS"],
    "experience_required": "5+ years",
    ...
  },
  "candidate": {
    "heading": "Senior Developer | Python & React",
    "experience_years": 7,
    "skills": [{"name": "Python", "level": "Expert"}],
    ...
  }
}
```

**Response:**
```json
{
  "liked": true,
  "compatibility": 88,
  "reason": "The candidate demonstrates excellent technical skills...",
  "ai_swipe_reasons": [
    "Technical Skills (90/100): ...",
    "Career Trajectory (90/100): ...",
    "Cultural Fit (85/100): ..."
  ]
  "qa_required_human_review": false
}
```

### Python Library Usage

```python
from src.api.dependencies import get_container
from src.config import get_settings, setup_logging
from tests import create_mock_good_candidate

# Setup
settings = get_settings()
setup_logging(settings)

# Initialize
container = get_container()
await container.initialize(settings)

# Evaluate
request = create_mock_good_candidate()
result = await container.evaluation_service.evaluate(request)

print(f"Decision: {'LIKED' if result.liked else 'REJECTED'}")
print(f"Score: {result.compatibility}/100")
```

## 📁 Project Structure

```
test-evaluate-agents/
├── src/                      # Source code
│   ├── agents/               # AI agent implementations
│   ├── api/                  # FastAPI application
│   ├── config/               # Configuration management
│   ├── graph/                # LangGraph workflow
│   ├── models/               # Pydantic data models
│   └── services/             # Business logic
├── tests/                    # Test suite
├── docs/                     # Documentation
│   ├── architecture/         # Architecture docs
│   ├── guides/               # User guides
│   └── development/          # Developer docs
├── main.py                   # Entry point
└── requirements.txt          # Dependencies
```

## 🧪 Testing

The system includes comprehensive integration tests:

```bash
# Run all tests
python main.py --test

# Results are saved to evaluation_results/
ls evaluation_results/
# good_candidate_20251104_154453.json
# bad_candidate_20251104_154509.json
```

### Test Scenarios

- ✅ **Good Candidate**: Senior dev with 7 years exp → LIKED (88/100)
- ❌ **Bad Candidate**: Junior dev with 2 years exp → REJECTED (10/100)

## 📊 Evaluation Criteria

### Technical Skills (50% weight)
- Mandatory skills match
- Nice-to-have skills coverage
- Technical experience depth
- Relevant technologies expertise

### Career Trajectory (35% weight)
- Years of experience adequacy
- Career progression clarity
- Role relevance history
- Company prestige alignment

### Cultural Fit (15% weight)
- Language proficiency match
- Work style compatibility
- Contract type alignment
- Geographic/remote flexibility

### QA Validation
- **Rule 1**: Flags if score ≥70 but technical <50
- **Rule 2**: Flags if score <70 but all scores >80

## 📚 Documentation

Complete documentation is available in the [`docs/`](docs/) directory:

- **[📖 Documentation Index](docs/README.md)** - Complete documentation navigation
- **[🏗️ Architecture](docs/architecture/)** - System design and architecture
  - [Architecture Overview](docs/architecture/ARCHITECTURE.md)
  - [Refactoring Guide](docs/architecture/REFACTORING_GUIDE.md)
- **[📘 User Guides](docs/guides/)** - Step-by-step guides
  - [Quick Start Guide](docs/guides/QUICKSTART.md)
  - [Evaluation Logs Guide](docs/guides/EVALUATION_LOGS.md)
- **[👨‍💻 Development](docs/development/)** - Developer documentation
  - [Requirements Checklist](docs/development/CHECKLIST_REQUIREMENTS.md)
  - [Project Summary](docs/development/PROJECT_SUMMARY.md)

## 🛠️ Technology Stack

- **Framework**: FastAPI 0.104+
- **AI/LLM**: OpenAI GPT-4o-mini
- **Orchestration**: LangGraph (LangChain)
- **Validation**: Pydantic v2
- **Configuration**: pydantic-settings
- **Server**: Uvicorn
- **Python**: 3.11+

## 🔧 Configuration

Environment variables (`.env`):

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.2
LOG_LEVEL=INFO
```

## 📈 Performance

- **Average evaluation time**: ~40 seconds
- **Agents execution**: 5 sequential agents
- **API response time**: <45 seconds
- **Concurrent requests**: Supports multiple parallel evaluations

## 🔒 Security

- API key validation
- Input sanitization with Pydantic
- Error handling and logging
- No sensitive data in logs

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](docs/development/CONTRIBUTING.md).

## 📝 License

[Add your license here]

## 👥 Authors

- Development Team
- AI Architecture: OpenAI GPT-4o-mini
- Framework: LangGraph

## 🙏 Acknowledgments

- LangChain/LangGraph team
- FastAPI team
- OpenAI

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Contact: [your-email@example.com]

---

**Version**: 1.0.0  
**Last Updated**: November 2025  
**Status**: Production Ready ✅
