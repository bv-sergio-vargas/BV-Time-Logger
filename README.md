# BV-Time-Logger

Agente automatizado que sincroniza los tiempos de reuniones de Microsoft Teams con las tareas de Azure DevOps para registrar con precisión las horas reales trabajadas. Compara las duraciones de sesiones reales con los tiempos programados y actualiza las entradas de work items, mejorando el seguimiento del tiempo y la eficiencia en la gestión de proyectos.

## 🚀 Inicio Rápido

**¿Nuevo en el proyecto?** Comienza aquí: [01-QUICKSTART.md](docs/01-QUICKSTART.md) (15 minutos)

## 📋 Documentación

- **[00-TOC.md](docs/00-TOC.md)** - Tabla de contenidos completa
- **[01-QUICKSTART.md](docs/01-QUICKSTART.md)** - Configuración inicial en 15 minutos
- **[02-REQUIREMENTS.md](docs/02-REQUIREMENTS.md)** - Requerimientos funcionales y no funcionales
- **[03-PROJECT_PHASES.md](docs/03-PROJECT_PHASES.md)** - Plan detallado de implementación por fases
- **[04-AZURE_SETUP_GUIDE.md](docs/04-AZURE_SETUP_GUIDE.md)** - Guía completa de configuración Azure
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** - Guía para agentes de IA

## ✨ Características Principales

- ✅ **Sincronización automática** de reuniones de Microsoft Teams
- ✅ **Actualización de work items** en Azure DevOps con resolución de conflictos
- ✅ **Comparación** de tiempo real vs estimado (4 niveles de desviación)
- ✅ **Reportes detallados** (CSV/JSON) con recomendaciones en español
- ✅ **Tracking manual** con CLI (CSV import/export, validaciones)
- ✅ **Scheduler automático** (diario/intervalo/cron personalizado)
- ✅ **Logging robusto** con rotación (10MB) y mensajes en español
- ✅ **CLI completo** con 9 comandos (sync, manual, schedule, report, status)
- ✅ **Modo dry-run** para preview sin cambios reales
- ✅ **Auditoría completa** con historial de ejecuciones

## 🏗️ Estado del Proyecto

**Fase Actual**: Fases 5-6 COMPLETADAS ✅ (Orquestación y Manual Tracking)

**Completado**:
- ✅ **Fase 0-1**: Configuración y autenticación (Microsoft Graph + Azure DevOps)
- ✅ **Fase 2**: Integración Microsoft Teams (reuniones y procesamiento)
- ✅ **Fase 3**: Integración Azure DevOps (work items y actualizaciones)
- ✅ **Fase 4**: Comparación de tiempos y generación de reportes
- ✅ **Fase 5**: Orquestación completa, scheduler automático, sistema de logging
- ✅ **Fase 6**: Tracking manual, CLI con 9 comandos
- 📊 **84 tests** de Fases 1-4 + **86 tests** de Fases 5-6

**Próximo**: Fase 7 - Testing completo y validación end-to-end

Ver roadmap completo en [03-PROJECT_PHASES.md](docs/03-PROJECT_PHASES.md)

## 🛠️ Tecnologías

- **Lenguaje**: Python 3.13+ (type hints, async support)
- **APIs**: Microsoft Graph API, Azure DevOps REST API
- **Autenticación**: MSAL OAuth 2.0 (Microsoft), PAT (Azure DevOps)
- **Scheduling**: APScheduler 3.11+ (CronTrigger, IntervalTrigger)
- **Testing**: pytest 9.0+ (170 tests total)
- **Cloud**: Azure (Key Vault, Functions, Application Insights)
- **Timezone**: America/Bogota (pytz)

## 📦 Instalación

### Instalación Rápida (5 minutos)

```powershell
# 1. Clonar repositorio
git clone https://github.com/bigview-sas/BV-Time-Logger.git
cd BV-Time-Logger

# 2. Crear y activar entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
Copy-Item .env.template .env
# Editar .env con tus credenciales (ver guía abajo)

# 5. Validar accesos
python validate_access.py
```

### Configuración de Credenciales

Antes de ejecutar el script de validación, debes configurar:

1. **Azure DevOps PAT** - Ver guía: [04-AZURE_SETUP_GUIDE.md](docs/04-AZURE_SETUP_GUIDE.md#1-configuración-de-azure-devops)
2. **Azure AD App Registration** - Ver guía: [04-AZURE_SETUP_GUIDE.md](docs/04-AZURE_SETUP_GUIDE.md#2-configuración-de-azure-ad)

### Validación de Instalación

```powershell
# Activar entorno (si no está activo)
.\venv\Scripts\Activate.ps1

# Ejecutar script de validación
python validate_access.py

# Salida esperada:
# ✅ Azure DevOps: PASS
# ✅ Microsoft Graph: PASS
```

Ver guía completa en [01-QUICKSTART.md](docs/01-QUICKSTART.md) y [04-AZURE_SETUP_GUIDE.md](docs/04-AZURE_SETUP_GUIDE.md)

## 🖥️ Uso del CLI

### Comandos Disponibles

```powershell
# Sincronización manual
python -m src.cli sync --start-date 2026-01-01 --end-date 2026-01-31

# Entrada manual de tiempo
python -m src.cli manual -w 12345 -H 8.0 -d 2026-01-30 -D "Development work" -u user@example.com

# Importar desde CSV
python -m src.cli import entradas.csv --sync

# Exportar a CSV
python -m src.cli export reporte.csv --start-date 2026-01-01 --end-date 2026-01-31

# Listar entradas manuales
python -m src.cli list --user user@example.com

# Ver resumen
python -m src.cli summary

# Configurar scheduler (ejecución diaria a las 9:00 AM)
python -m src.cli schedule start --daily --time 09:00

# Estado del scheduler
python -m src.cli schedule status

# Generar reporte
python -m src.cli report --format csv --sync

# Ver estado del sistema
python -m src.cli status
```

### Modo Dry-Run (Preview)

```powershell
# Preview sin aplicar cambios
python -m src.cli sync --dry-run
```

### Opciones Avanzadas

```powershell
# Sincronización con usuarios específicos
python -m src.cli sync --users user1@example.com user2@example.com

# Scheduler con intervalo de 2 horas
python -m src.cli schedule start --interval 2

# Scheduler con expresión cron personalizada (9 AM lunes a viernes)
python -m src.cli schedule start --cron "0 9 * * 1-5"

# Exportar solo entradas sincronizadas
python -m src.cli export reporte.csv --synced true
```

## 🎯 Casos de Uso

1. **Equipos de desarrollo** que necesitan tracking preciso de horas
2. **Project Managers** que requieren reportes de tiempo real vs estimado
3. **Organizaciones** que buscan mejorar estimaciones y planificación
4. **Compliance** para auditoría de horas trabajadas

## 📊 Flujo de Trabajo

```
Microsoft Teams → Obtener reuniones → Calcular duración
                                              ↓
Azure DevOps ← Actualizar work items ← Comparar tiempos
                                              ↓
                                      Generar reportes
```

## 🤝 Contribuir

1. Fork el proyecto
2. Crear feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add: AmazingFeature'`)
4. Push a branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📄 Licencia

Este proyecto está licenciado bajo [LICENSE](LICENSE)

## 👥 Equipo

**Bigview SAS** - Soluciones empresariales en Colombia

## 📞 Soporte

- 📧 Email: soporte@bigview.com.co
- 🐛 Issues: [GitHub Issues](https://github.com/bigview-sas/BV-Time-Logger/issues)
- 📖 Docs: [00-TOC.md](docs/00-TOC.md)

---

**Desarrollado con ❤️ por Bigview SAS**
