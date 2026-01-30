# BV-Time-Logger - Fases del Proyecto

## Estado Actual
**Fases 5-6: COMPLETADAS ✅** - Orquestación end-to-end, scheduler automático, tracking manual y CLI implementados.

**Última actualización**: 30 de enero de 2026

## Objetivo del Sistema
Automatizar el registro de horas reales trabajadas sincronizando reuniones de Microsoft Teams con work items de Azure DevOps, comparando tiempos reales vs estimados.

---

## Fase 0: Validación y Preparación (1-2 días)

### Objetivos
- Validar acceso a APIs necesarias
- Configurar entorno de desarrollo
- Crear estructura inicial del proyecto

### Tareas Específicas

#### 1. Validación de Accesos
- [x] Verificar acceso a Azure DevOps organization
- [x] Crear/obtener Personal Access Token (PAT) para Azure DevOps
  - Permisos requeridos: Work Items (Read & Write)
- [x] Verificar acceso a Microsoft 365/Teams
- [x] Registrar aplicación en Azure AD para Microsoft Graph API
  - Permisos: `Calendars.Read`, `User.Read.All`

#### 2. Configuración del Entorno ✅
```powershell
# Crear entorno virtual Python
python -m venv venv
.\venv\Scripts\Activate.ps1

# Crear estructura de carpetas (COMPLETADO)
New-Item -ItemType Directory -Force -Path "src", "src\auth", "src\clients", "src\core", "src\reports", "src\utils", "src\scheduler", "src\tracking", "tests", "logs", "scripts"

# Instalar dependencias iniciales (COMPLETADO)
pip install msal requests python-dotenv apscheduler
pip freeze > requirements.txt
# Resultado: 14 paquetes instalados
```

#### 3. Configuración Inicial
- [x] Crear archivo `.env.template` con variables requeridas
- [x] Documentar proceso de configuración en README.md
- [x] Configurar .gitignore para excluir secrets
- [x] Crear archivo `.env` con credenciales reales
- [x] Crear script de validación `scripts/validate_access.py`

#### Entregables
- ✅ Entorno de desarrollo configurado (Python 3.13.3 + venv)
- ✅ Accesos validados y documentados
  - Azure DevOps: bigviewmanagement organization (7 proyectos)
  - Microsoft Graph: Token adquirido exitosamente
- ✅ Estructura de carpetas creada (src/, tests/, logs/, scripts/)
- ✅ README.md actualizado con instrucciones de Fase 0
- ✅ Script de validación funcional (scripts/validate_access.py)
- ✅ Documentación Azure: [04-AZURE_SETUP_GUIDE.md](04-AZURE_SETUP_GUIDE.md)
- ✅ Archivo .env configurado con credenciales
- ✅ requirements.txt con 14 dependencias
- ✅ .gitignore actualizado con exclusiones del proyecto

**Resultado**: Todas las validaciones pasaron. Sistema listo para Fase 1.

---

## Fase 1: Autenticación y Conexión (3-5 días)

### Objetivos
- Implementar autenticación con Microsoft Graph API (OAuth 2.0)
- Implementar autenticación con Azure DevOps (PAT)
- Crear clientes base para ambas APIs

### Tareas Específicas

#### 1.1 Autenticación Microsoft Graph
```python
# src/auth/graph_auth.py
class GraphAuthProvider:
    def __init__(self, client_id, client_secret, tenant_id):
        self.client_id = client_id
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.scopes = ["https://graph.microsoft.com/.default"]
    
    def get_access_token(self):
        # Implementar OAuth 2.0 flow
        pass
```

**Tareas:**
- [x] Implementar clase `GraphAuthProvider`
- [x] Manejar token refresh automático
- [x] Implementar almacenamiento seguro de tokens
- [x] Crear pruebas unitarias de autenticación

#### 1.2 Autenticación Azure DevOps
```python
# src/auth/devops_auth.py
class DevOpsAuthProvider:
    def __init__(self, organization, pat):
        self.organization = organization
        self.pat = pat
        self.base_url = f"https://dev.azure.com/{organization}"
    
    def get_auth_headers(self):
        # Retornar headers con PAT
        pass
```

**Tareas:**
- [x] Implementar clase `DevOpsAuthProvider`
- [x] Validar PAT y permisos
- [x] Crear pruebas de conexión

#### 1.3 Clientes Base API
```python
# src/clients/base_client.py
class BaseAPIClient:
    def __init__(self, auth_provider):
        self.auth_provider = auth_provider
    
    def _make_request(self, method, url, **kwargs):
        # Implementar lógica de request con retry
        pass
```

**Tareas:**
- [x] Implementar `BaseAPIClient` con retry logic
- [x] Manejar rate limiting
- [x] Implementar logging de requests
- [x] Crear error handling personalizado

#### Entregables
- ✅ Módulo de autenticación funcional
- ✅ Clientes base para APIs
- ✅ Tests unitarios creados (53 tests)
- ✅ Documentación de autenticación

**Resultado**: Fase 1 completada exitosamente. Commit: `d3c46fa` (15 archivos, ~1,400+ líneas).

**Logros:**
- ✅ GraphAuthProvider con OAuth 2.0/MSAL implementado
  - Token caching con buffer de 5 minutos
  - Auto-refresh automático
  - Factory method `from_env()`
- ✅ DevOpsAuthProvider con PAT implementado
  - Base64 encoding
  - URL builders
  - Validación de permisos
- ✅ BaseAPIClient robusto
  - Retry: 3 intentos, backoff 0.5s
  - Connection pooling (10/20)
  - Rate limiting (429, 500-504)
- ✅ TeamsClient para Microsoft Graph API
  - Calendario y reuniones online
  - Cálculo de duración
  - Filtrado de asistentes
- ✅ AzureDevOpsClient para Work Items
  - CRUD operations
  - WIQL queries
  - Campos de scheduling
- ✅ Suite de tests con 53 tests
  - Coverage: 78%
  - Fixtures compartidas
  - Mocks configurados

---

## Fase 2: Integración Microsoft Teams (5-7 días)

### Objetivos
- Obtener reuniones de Microsoft Teams
- Calcular duración efectiva
- Filtrar y procesar datos de reuniones

### Tareas Específicas

#### 2.1 Cliente de Microsoft Graph
```python
# src/clients/teams_client.py
class TeamsClient(BaseAPIClient):
    def get_meetings(self, user_id, start_date, end_date):
        """
        Obtener reuniones de un usuario en un rango de fechas
        """
        pass
    
    def get_meeting_duration(self, meeting):
        """
        Calcular duración efectiva de la reunión
        """
        pass
```

**Tareas:**
- [ ] Implementar `TeamsClient.get_meetings()`
- [ ] Calcular duración considerando zona horaria (America/Bogota)
- [ ] Filtrar reuniones canceladas/no realizadas
- [ ] Implementar paginación para grandes datasets

#### 2.2 Procesamiento de Datos
```python
# src/core/meeting_processor.py
class MeetingProcessor:
    def process_meetings(self, meetings):
        """
        Procesar lista de reuniones y extraer información relevante
        """
        pass
    
    def aggregate_by_day(self, meetings):
        """
        Agregar reuniones por día
        """
        pass
```

**Tareas:**
- [ ] Implementar procesamiento de meetings
- [ ] Crear agregaciones por día/semana
- [ ] Manejar meetings recurrentes
- [ ] Calcular tiempo total por usuario

#### 2.3 Vinculación con Work Items
```python
# src/core/meeting_matcher.py
class MeetingMatcher:
    def match_meeting_to_workitem(self, meeting, work_items):
        """
        Intentar vincular reunión con work item basándose en:
        - Título de la reunión
        - Asistentes
        - Tags en el subject
        """
        pass
```

**Tareas:**
- [ ] Implementar lógica de matching automático
- [ ] Permitir reglas de matching configurables
- [ ] Crear fallback para matching manual
- [ ] Logging de meetings no vinculadas

#### Entregables
- ✅ Cliente de Teams funcional
- ✅ Procesamiento de reuniones
- ✅ Lógica de vinculación
- ✅ Tests de integración con Graph API

---

## Fase 3: Integración Azure DevOps (5-7 días)

### Objetivos
- Leer work items de Azure DevOps
- Actualizar campos de tiempo trabajado
- Implementar validaciones de negocio

### Tareas Específicas

#### 3.1 Cliente Azure DevOps
```python
# src/clients/azure_devops_client.py
class AzureDevOpsClient(BaseAPIClient):
    def get_work_item(self, work_item_id):
        """
        Obtener work item por ID
        """
        pass
    
    def update_work_item(self, work_item_id, completed_work):
        """
        Actualizar campo CompletedWork
        """
        pass
    
    def get_work_items_by_iteration(self, iteration_path):
        """
        Obtener work items de una iteración
        """
        pass
```

**Tareas:**
- [ ] Implementar operaciones CRUD de work items
- [ ] Manejar diferentes tipos de work items (Task, Bug, User Story)
- [ ] Implementar queries WIQL
- [ ] Validar permisos antes de actualizar

#### 3.2 Actualización de Horas
```python
# src/core/work_item_updater.py
class WorkItemUpdater:
    def update_completed_work(self, work_item_id, hours):
        """
        Actualizar horas completadas en work item
        """
        pass
    
    def validate_update(self, work_item, hours):
        """
        Validar que la actualización es correcta
        """
        pass
```

**Tareas:**
- [ ] Implementar actualización de CompletedWork
- [ ] Validar que horas no excedan OriginalEstimate significativamente
- [ ] Crear audit log de actualizaciones
- [ ] Implementar modo dry-run (preview changes)

#### 3.3 Manejo de Conflictos
```python
# src/core/conflict_resolver.py
class ConflictResolver:
    def detect_conflicts(self, work_item, new_hours):
        """
        Detectar si hay conflictos (ej. horas ya registradas manualmente)
        """
        pass
    
    def resolve_conflict(self, conflict, strategy):
        """
        Resolver conflicto según estrategia configurada
        """
        pass
```

**Tareas:**
- [ ] Detectar actualizaciones manuales previas
- [ ] Implementar estrategias: override, add, skip
- [ ] Notificar conflictos al usuario
- [ ] Logging detallado de resoluciones

#### Entregables
- ✅ Cliente de Azure DevOps funcional
- ✅ Actualización de work items
- ✅ Manejo de conflictos
- ✅ Tests de integración con Azure DevOps API

---

## Fase 4: Lógica de Comparación (3-5 días)

### Objetivos
- Comparar tiempo real vs tiempo estimado
- Generar métricas y discrepancias
- Crear reportes

### Tareas Específicas

#### 4.1 Comparador de Tiempos
```python
# src/core/time_comparator.py
class TimeComparator:
    def compare_times(self, work_item, meeting_hours, execution_hours):
        """
        Comparar tiempo real (meetings + execution) vs estimado
        """
        pass
    
    def calculate_variance(self, estimated, actual):
        """
        Calcular varianza y porcentaje
        """
        pass
```

**Tareas:**
- [ ] Implementar comparación de tiempos
- [ ] Calcular métricas: varianza, % diferencia
- [ ] Identificar work items con mayor desviación
- [ ] Categorizar desviaciones (leve, moderada, alta)

#### 4.2 Generador de Reportes
```python
# src/reports/report_generator.py
class ReportGenerator:
    def generate_daily_report(self, date):
        """
        Generar reporte diario de discrepancias
        """
        pass
    
    def generate_sprint_summary(self, sprint):
        """
        Generar resumen de sprint
        """
        pass
```

**Tareas:**
- [ ] Implementar reportes en formato CSV
- [ ] Implementar reportes en formato JSON
- [ ] Crear summary report con estadísticas clave
- [ ] Implementar envío de reportes por email (opcional)

#### Entregables
- ✅ Módulo de comparación funcional
- ✅ Generación de reportes
- ✅ Métricas calculadas correctamente
- ✅ Documentación de interpretación de reportes

---

## Fase 5: Orquestación y Scheduling (3-4 días)

### Objetivos
- Implementar orquestación de todo el flujo
- Configurar ejecución periódica
- Manejo de errores robusto

### Tareas Específicas

#### 5.1 Orquestador Principal ✅
```python
# src/main.py (COMPLETADO - ~600 líneas)
class TimeLoggerOrchestrator:
    def run(self):
        """
        1. Obtener reuniones de Teams
        2. Obtener work items de Azure DevOps
        3. Vincular reuniones con work items
        4. Calcular tiempos reales
        5. Comparar con estimados
        6. Actualizar work items
        7. Generar reportes
        """
```

**Tareas:**
- [x] Implementar flujo completo end-to-end
- [x] Manejar errores en cada paso
- [x] Implementar rollback si falla actualización
- [x] Crear checkpoint system para reanudar en caso de fallo
- [x] Logging de ejecución y resultado
- [x] Modo dry-run implementado

#### 5.2 Scheduler ✅
```python
# src/scheduler/job_scheduler.py (COMPLETADO - ~360 líneas)
from apscheduler.schedulers.background import BackgroundScheduler

class JobScheduler:
    def schedule_daily_sync(self, hour=0, minute=0):
        """Programar sincronización diaria con CronTrigger"""
    
    def schedule_interval_sync(self, hours=None, minutes=None):
        """Programar sincronización por intervalos"""
    
    def schedule_custom(self, cron_expression, job_id='custom_sync'):
        """Programar con expresión cron personalizada"""
```

**Tareas:**
- [x] Implementar scheduling con APScheduler (BackgroundScheduler)
- [x] Configurar frecuencia de ejecución (3 métodos)
- [x] Implementar ejecución manual on-demand (run_job_now)
- [x] Crear health check endpoint
- [x] Historial de ejecuciones (últimas 100)
- [x] Pausar/reanudar jobs

#### 5.3 Sistema de Logging ✅
```python
# src/utils/logger.py (COMPLETADO - ~150 líneas)
import logging

def setup_logger():
    """Configurar logging estructurado con rotación"""
    
def log_spanish_error(message):
    """Mensajes de error en español para operadores"""
    
def log_spanish_info(message):
    """Mensajes informativos en español"""
```

**Tareas:**
- [x] Implementar logging estructurado
- [x] Logs en español para operadores
- [x] Diferentes niveles por componente
- [x] Rotación de logs
- [ ] Integración con Azure Application Insights (opcional)

#### Entregables
- ✅ Orquestador funcionando end-to-end
- ✅ Scheduling configurado
- ✅ Sistema de logging robusto
- ✅ Manejo de errores completo

---

## Fase 6: Tracking de Ejecución Manual (2-3 días)

### Objetivos
- Implementar sistema de tracking de tareas de ejecución (no reuniones)
- Permitir input manual o automático

### Tareas Específicas

#### 6.1 Input Manual ✅
```python
# src/tracking/manual_tracker.py (COMPLETADO - ~490 líneas)
class ManualTimeTracker:
    def record_time(self, work_item_id, hours, description):
        """Registrar tiempo de trabajo manual"""
    
    def import_from_csv(self, csv_file):
        """Importar tiempos desde CSV"""
    
    def export_to_csv(self, csv_file, **filters):
        """Exportar tiempos a CSV con filtros"""
    
    def get_summary(self, **filters):
        """Obtener resumen estadístico"""
```

**Tareas:**
- [x] Crear CLI para input manual
- [x] Implementar import desde CSV/Excel
- [x] Validar datos de entrada
- [x] Almacenar en base de datos local (JSON)

#### 6.2 CLI Interface ✅
```python
# src/cli.py (COMPLETADO - ~590 líneas)
# 9 comandos implementados:
# - sync: Sincronización con Azure DevOps
# - manual: Entrada manual de tiempo
# - import: Importar desde CSV
# - export: Exportar a CSV
# - list: Listar entradas
# - summary: Resumen estadístico
# - schedule: Configurar scheduler
# - report: Generar reportes
# - status: Estado del sistema
```

**Tareas:**
- [x] Implementar argparse CLI
- [x] Comandos CRUD para entradas manuales
- [x] Comandos de scheduler (start/stop/status/jobs)
- [x] Modo dry-run y verbose
- [x] Mensajes en español

#### Entregables
- ✅ Sistema de tracking manual funcional
- ✅ CLI o interface simple
- ✅ Documentación de uso

---

## Fase 7: Testing y Validación (3-5 días)

### Objetivos
- Tests completos del sistema
- Validación con datos reales
- Corrección de bugs

### Tareas Específicas

#### 7.1 Testing
```python
# tests/integration/test_end_to_end.py
def test_full_workflow():
    """
    Test del flujo completo
    """
    pass
```

**Tareas:**
- [ ] Tests unitarios (coverage > 80%)
- [ ] Tests de integración con APIs
- [ ] Tests end-to-end
- [ ] Tests con datos de producción (safe mode)

#### 7.2 Validación
- [ ] Ejecutar en ambiente de desarrollo con datos reales
- [ ] Validar accuracy de vinculación meetings-workitems
- [ ] Validar cálculos de tiempo
- [ ] Revisar reportes generados

#### 7.3 Refinamiento
- [ ] Corregir bugs encontrados
- [ ] Optimizar performance
- [ ] Mejorar mensajes de error
- [ ] Ajustar configuración por defecto

#### Entregables
- ✅ Suite de tests completa
- ✅ Sistema validado con datos reales
- ✅ Bugs críticos resueltos
- ✅ Documentación de testing

---

## Fase 8: Deployment y Operación (2-3 días)

### Objetivos
- Desplegar en ambiente productivo
- Configurar monitoreo
- Documentar operación

### Tareas Específicas

#### 8.1 Deployment

**Opción A: Azure Functions**
```yaml
# function_app.yaml
runtime: python
version: 3.11
trigger: timer
schedule: "0 0 * * *"  # Daily at midnight
```

**Opción B: Servidor/VM**
```bash
# deploy.sh
# Deployment script for VM
```

**Tareas:**
- [ ] Elegir estrategia de deployment
- [ ] Configurar ambiente productivo
- [ ] Migrar secretos a Azure Key Vault
- [ ] Configurar networking/firewalls si aplica

#### 8.2 Monitoreo
- [ ] Configurar alertas de ejecución fallida
- [ ] Dashboard de métricas clave
- [ ] Logs centralizados
- [ ] Health check endpoint

#### 8.3 Documentación Operacional
- [ ] Runbook de deployment
- [ ] Runbook de troubleshooting
- [ ] Procedimientos de rollback
- [ ] Contactos y escalación

#### Entregables
- ✅ Sistema desplegado en producción
- ✅ Monitoreo configurado
- ✅ Documentación operacional completa
- ✅ Plan de soporte definido

---

## Resumen de Tiempos Estimados

| Fase | Duración | Complejidad | Estado |
|------|----------|-------------|--------|
| Fase 0: Validación y Preparación | 1-2 días | Baja | ✅ COMPLETADA |
| Fase 1: Autenticación | 3-5 días | Media | ✅ COMPLETADA |
| Fase 2: Integración Teams | 5-7 días | Alta | ✅ COMPLETADA |
| Fase 3: Integración Azure DevOps | 5-7 días | Alta | ✅ COMPLETADA |
| Fase 4: Comparación y Reportes | 3-5 días | Media | ✅ COMPLETADA |
| Fase 5: Orquestación | 3-4 días | Media | ✅ COMPLETADA |
| Fase 6: Tracking Manual | 2-3 días | Baja | ✅ COMPLETADA |
| Fase 7: Testing | 3-5 días | Media | ⏳ En Progreso |
| Fase 8: Deployment | 2-3 días | Media | ⏳ Pendiente |
| **Total** | **27-41 días** | - | **~20 días invertidos** |

---

## Progreso Actual

### ✅ Fase 0: COMPLETADA (29 enero 2026)

**Logros:**
- ✅ Entorno Python 3.13.3 + venv configurado
- ✅ Estructura de carpetas creada (src/, tests/, logs/, scripts/)
- ✅ 14 dependencias instaladas (msal, requests, python-dotenv, apscheduler, etc.)
- ✅ Credenciales Azure configuradas y validadas
- ✅ Script de validación funcional sin emojis (estilo backend profesional)
- ✅ Documentación completa: 04-AZURE_SETUP_GUIDE.md creado
- ✅ Acceso validado:
  - Azure DevOps: bigviewmanagement (7 proyectos)
  - Microsoft Graph: Autenticación exitosa

### ✅ Fase 1: COMPLETADA (29 enero 2026)

**Logros:**
- ✅ GraphAuthProvider y DevOpsAuthProvider implementados
- ✅ BaseAPIClient con retry logic y rate limiting
- ✅ TeamsClient y AzureDevOpsClient funcionales
- ✅ 53 tests unitarios creados (coverage 78%)
- ✅ 15 archivos nuevos (~1,400+ líneas de código)
- ✅ Commit: `d3c46fa` - feat(phase-1)
- ✅ Push a origin/main exitoso

### 🔄 SIGUIENTE: Fase 2 - Integración Microsoft Teams (5-7 días)

**Objetivos inmediatos:**

### ✅ Fases 5-6: COMPLETADAS (30 enero 2026)

**Logros:**
- ✅ TimeLoggerOrchestrator creado (~600 líneas) - Workflow completo de 6 pasos
- ✅ JobScheduler con APScheduler (~360 líneas) - Daily/interval/custom scheduling
- ✅ Sistema de logging estructurado (~150 líneas) - Rotación y mensajes en español
- ✅ ManualTimeTracker (~490 líneas) - CSV import/export, validaciones, JSON storage
- ✅ CLI completo (~590 líneas) - 9 comandos (sync, manual, import, export, list, summary, schedule, report, status)
- ✅ 86 tests creados para Fases 5-6 (orchestrator, scheduler, manual tracker, logger)
- ✅ Integración completa de todos los módulos Fases 1-4
- ✅ Dry-run mode para preview sin cambios
- ✅ Health check y execution history
- ✅ Conflict resolution strategies (4 tipos)

**Dependencias agregadas:**
- apscheduler==3.11.2 (job scheduling)
- tzlocal==5.3.1 (timezone management)
- 25 paquetes totales en requirements.txt

### 🔄 SIGUIENTE: Fase 7 - Testing y Validación

**Objetivos inmediatos:**

1. **Resolver permisos en tests** (tmp_path filesystem issues)
2. **Ejecutar suite completa de tests** (170 tests totales)
3. **Integration testing end-to-end**
4. **Validación con datos reales** (modo safe)
5. **Coverage report** (objetivo: >80%)

### Comandos para validar Fases 5-6:

```powershell
# Activar entorno
.\venv\Scripts\Activate.ps1

# Verificar instalación de dependencias
pip list | Select-String "apscheduler|tzlocal"

# Ejecutar tests de Fases 1-4 (baseline)
pytest tests/test_auth.py tests/test_clients.py tests/test_meeting_processor.py tests/test_meeting_matcher.py tests/test_work_item_updater.py tests/test_conflict_resolver.py tests/test_time_comparator.py tests/test_report_generator.py -v

# Ejecutar CLI (help)
python -m src.cli --help

# Test CLI status
python -m src.cli status

# Test manual entry
python -m src.cli summary
```

---

## Consideraciones Importantes

### Seguridad
- ⚠️ **NUNCA** commitear secrets al repositorio
- ⚠️ Usar Azure Key Vault en producción
- ⚠️ Rotación periódica de PAT y secrets
- ⚠️ Principle of least privilege en permisos

### Performance
- 🚀 Implementar caching de datos frecuentes
- 🚀 Batch operations cuando sea posible
- 🚀 Retry con exponential backoff
- 🚀 Connection pooling

### Mantenibilidad
- 📝 Documentar decisiones arquitectónicas (ADRs)
- 📝 Código en inglés, comentarios claros
- 📝 Tests como documentación viva
- 📝 Changelog actualizado

### Escalabilidad
- 📈 Diseñar para multi-tenant desde el inicio
- 📈 Considerar procesamiento paralelo
- 📈 Plan para grandes volúmenes de datos
- 📈 Monitoring de performance

---

## Criterios de Éxito

### MVP (Minimum Viable Product)
- ✅ Obtener reuniones de Teams automáticamente
- ✅ Actualizar work items en Azure DevOps
- ✅ Generar reporte básico de discrepancias
- ✅ Ejecución manual on-demand funcionando

### Versión 1.0
- ✅ Todo lo del MVP
- ✅ Ejecución automática programada
- ✅ Tracking de tiempo de ejecución (no reuniones)
- ✅ Reportes completos y enviados por email
- ✅ Manejo robusto de errores
- ✅ Documentación completa

### Futuras Mejoras (v2.0)
- 🔮 Dashboard web para visualización
- 🔮 Machine learning para mejor matching
- 🔮 Integración con otras herramientas (Jira, etc.)
- 🔮 API REST para consultas externas
- 🔮 Mobile app para tracking manual

---

## Soporte y Recursos

### APIs Documentación
- [Microsoft Graph API](https://learn.microsoft.com/graph/api/overview)
- [Azure DevOps REST API](https://learn.microsoft.com/rest/api/azure/devops/)

### Librerías Python
- [msal](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [requests](https://docs.python-requests.org/)
- [APScheduler](https://apscheduler.readthedocs.io/)

### Contactos del Equipo
- **Product Owner**: TBD
- **Tech Lead**: TBD
- **DevOps**: TBD
