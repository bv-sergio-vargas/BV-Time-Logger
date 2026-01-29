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
- ✅ **Actualización de work items** en Azure DevOps
- ✅ **Comparación** de tiempo real vs estimado
- ✅ **Reportes de discrepancias** para gestión de proyectos
- ✅ **Registro de tiempo de ejecución** (tareas sin reuniones)
- ✅ **Logging y auditoría** completa

## 🏗️ Estado del Proyecto

**Fase Actual**: Fase 0 - Validación y Preparación ✅

**Completado**:
- ✅ Estructura de carpetas creada
- ✅ Entorno virtual Python configurado
- ✅ Dependencias instaladas
- ✅ Script de validación de accesos creado
- ✅ Documentación de configuración Azure

**Próximo**: Fase 1 - Autenticación y Conexión

Ver roadmap completo en [03-PROJECT_PHASES.md](docs/03-PROJECT_PHASES.md)

## 🛠️ Tecnologías

- **Lenguaje**: Python 3.9+
- **APIs**: Microsoft Graph API, Azure DevOps REST API
- **Autenticación**: OAuth 2.0 (Microsoft), PAT (Azure DevOps)
- **Cloud**: Azure (Key Vault, Functions, Application Insights)

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
