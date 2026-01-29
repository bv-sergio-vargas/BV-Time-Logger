# BV-Time-Logger - AI Agent Instructions

## Project Overview

**BV-Time-Logger** is an automation agent that synchronizes Microsoft Teams meeting durations with Azure DevOps work items to accurately track and log real work hours. The system compares actual time spent (meetings + execution tasks) against scheduled Azure DevOps task estimates and automatically updates work items.

**Status**: Early stage - no implementation code yet. Requirements defined in [02-REQUIREMENTS.md](../docs/02-REQUIREMENTS.md).

## Core Objectives

1. **RF1**: Retrieve actual meeting duration from Microsoft Teams (per team member)
2. **RF2**: Track execution task hours not associated with meetings
3. **RF3**: Compare real time (meetings + execution) vs. Azure DevOps scheduled time
4. **RF4**: Auto-update work item hours in Azure DevOps
5. **RF5**: Generate discrepancy reports (planned vs. actual)
6. **RF6**: Configurable execution frequency
7. **RF7**: Activity and error logging for audit and monitoring

## Technical Architecture

### Integration Points

1. **Microsoft Graph API** - Retrieve Teams meeting data
   - OAuth authentication required
   - Endpoint: `/me/calendarView` or `/users/{id}/events`
   - Fetch: meeting duration, attendees, subject

2. **Azure DevOps REST API** - Work item management
   - PAT (Personal Access Token) authentication
   - Endpoints:
     - `GET /_apis/wit/workitems/{id}` - Read work items
     - `PATCH /_apis/wit/workitems/{id}` - Update completed work field
   - Fields: `Microsoft.VSTS.Scheduling.CompletedWork`, `Microsoft.VSTS.Scheduling.OriginalEstimate`

3. **Execution Time Tracking**
   - Method TBD: Desktop activity monitoring, manual input, or time-tracking service integration

### Recommended Technology Stack

Based on .gitignore (Python-focused), consider:
- **Language**: Python 3.9+
- **Auth**: `msal` (Microsoft Authentication Library) for OAuth
- **HTTP**: `requests` or `httpx` for API calls
- **Scheduling**: `APScheduler` or Azure Functions timer trigger
- **Config**: Environment variables or Azure Key Vault for secrets
- **Logging**: Python `logging` module with structured output

## Implementation Phases

**📋 Ver documento completo de fases:** [03-PROJECT_PHASES.md](../docs/03-PROJECT_PHASES.md)

### Resumen de Fases (27-41 días totales)

**Fase 0: Validación y Preparación** (1-2 días)
- Validar accesos a APIs (Azure DevOps PAT, Azure AD App Registration)
- Configurar entorno de desarrollo Python
- Crear estructura inicial del proyecto

**Fase 1: Autenticación** (3-5 días)
- Implementar OAuth 2.0 para Microsoft Graph API
- Implementar PAT authentication para Azure DevOps
- Crear clientes base con retry logic y error handling

**Fase 2: Integración Microsoft Teams** (5-7 días)
- Cliente para obtener reuniones vía Graph API
- Procesamiento y cálculo de duración efectiva
- Lógica de vinculación meeting → work item

**Fase 3: Integración Azure DevOps** (5-7 días)
- Cliente para leer/actualizar work items
- Actualización de campo CompletedWork
- Manejo de conflictos y validaciones

**Fase 4: Comparación y Reportes** (3-5 días)
- Lógica de comparación tiempo real vs estimado
- Generación de reportes (CSV, JSON)
- Cálculo de métricas y varianzas

**Fase 5: Orquestación** (3-4 días)
- Flujo completo end-to-end
- Scheduling automático (APScheduler o Azure Functions)
- Sistema de logging robusto

**Fase 6: Tracking Manual** (2-3 días)
- Input manual de horas de ejecución
- CLI o import desde CSV
- Almacenamiento local de datos

**Fase 7: Testing** (3-5 días)
- Tests unitarios e integración
- Validación con datos reales
- Corrección de bugs

**Fase 8: Deployment** (2-3 días)
- Despliegue a producción (Azure Functions o VM)
- Configuración de monitoreo
- Documentación operacional

### Para Empezar HOY
```powershell
# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# 2. Crear estructura
mkdir src, tests, docs, config

# 3. Archivo de dependencias
pip install msal requests python-dotenv apscheduler
pip freeze > requirements.txt

# 4. Verificar accesos
# - Azure DevOps: Crear PAT con permisos Work Items (Read & Write)
# - Azure AD: Registrar app para Graph API (Calendars.Read, User.Read)
```

## Security & Compliance

- **Never commit secrets**: Use `.env` files (in `.gitignore`) or Azure Key Vault
- **PAT Storage**: Store securely with minimal required permissions (Work Items: Read & Write)
- **OAuth Tokens**: Implement secure token refresh flows
- **Audit Trail**: Log all work item modifications with timestamp and user context
- **Data Privacy**: Handle meeting/user data per organizational policies

## Development Conventions

- **Language**: Code and documentation in **English**; user-facing logs/reports in **Spanish (Colombian)** if applicable
- **Modular Design**: Separate concerns (auth, API clients, business logic, scheduling)
- **Error Handling**: Implement retries for network failures (exponential backoff)
- **Testing**: Unit tests for core logic modules
- **Versioning**: Use Git flow (dev, staging, main branches)
- **Documentation**: Keep README.md and inline docstrings updated

## Key Files (When Implemented)

- `config.py` or `.env` - Configuration and secrets
- `auth/` - Authentication modules for Graph API and Azure DevOps
- `clients/teams_client.py` - Microsoft Teams/Graph API interactions
- `clients/azure_devops_client.py` - Azure DevOps API interactions
- `core/time_aggregator.py` - Time calculation and comparison logic
- `core/work_item_updater.py` - Work item update orchestration
- `utils/logger.py` - Centralized logging configuration
- `main.py` - Entry point and orchestration

## Common Commands (Once Implemented)

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py

# Run tests
pytest tests/

# Deploy to Azure Functions (if applicable)
func azure functionapp publish <function-app-name>
```

## Notes for AI Agents

- This is a **greenfield project** - no legacy code constraints
- Prioritize **security** (credential management) and **reliability** (error handling, retries)
- Design for **scalability** - support varying team sizes without performance degradation
- Follow **Azure DevOps API best practices**: rate limiting, field validation, proper PATCH operations
- Consider **multi-tenant scenarios** if multiple teams/projects need tracking
