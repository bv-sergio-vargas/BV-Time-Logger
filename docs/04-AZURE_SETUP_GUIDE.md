# Guía de Configuración de Azure

Esta guía documenta paso a paso cómo configurar los accesos necesarios para BV-Time-Logger en Azure DevOps y Azure AD.

---

## Índice

1. [Configuración de Azure DevOps](#1-configuración-de-azure-devops)
2. [Configuración de Azure AD](#2-configuración-de-azure-ad)
3. [Configuración del Archivo .env](#3-configuración-del-archivo-env)
4. [Validación de Accesos](#4-validación-de-accesos)

---

## 1. Configuración de Azure DevOps

### 1.1 Crear Personal Access Token (PAT)

1. **Acceder a Azure DevOps**
   - Ir a: https://dev.azure.com/{tu-organización}
   - Hacer clic en tu avatar (esquina superior derecha)
   - Seleccionar "Personal access tokens"

2. **Crear Nuevo Token**
   - Clic en "+ New Token"
   - Configurar:
     - **Name**: `BV-Time-Logger-PAT`
     - **Organization**: Seleccionar tu organización
     - **Expiration**: 90 días (o según política de seguridad)
     - **Scopes**: Custom defined

3. **Configurar Permisos (Scopes)**
   - ✅ **Work Items**: Read & Write
   - ✅ **Project and Team**: Read
   - ⚠️ **Importante**: Solo otorgar permisos mínimos necesarios

4. **Copiar Token**
   - Clic en "Create"
   - **COPIAR EL TOKEN INMEDIATAMENTE** (no se podrá ver después)
   - Guardar temporalmente en un lugar seguro

5. **Probar PAT**
   ```powershell
   # PowerShell - Reemplazar {PAT} y {organization}
   $pat = "tu-pat-aqui"
   $org = "tu-organizacion"
   $base64Pat = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$pat"))
   
   $headers = @{
       Authorization = "Basic $base64Pat"
   }
   
   $url = "https://dev.azure.com/$org/_apis/projects?api-version=7.1"
   Invoke-RestMethod -Uri $url -Headers $headers -Method Get
   ```

### 1.2 Identificar Organización y Proyecto

- **Organización**: Visible en la URL: `https://dev.azure.com/{ORGANIZACIÓN}`
- **Proyecto**: Nombre del proyecto donde se gestionan los work items
  - Ejemplo: `BV-Internal-Tools`, `ProductDevelopment`, etc.

---

## 2. Configuración de Azure AD

### 2.1 Registrar Aplicación en Azure AD

1. **Acceder al Portal de Azure**
   - Ir a: https://portal.azure.com
   - Buscar "Azure Active Directory" (o "Microsoft Entra ID")

2. **Crear Registro de Aplicación**
   - Menú lateral: "App registrations" → "+ New registration"
   - Configurar:
     - **Name**: `BV-Time-Logger`
     - **Supported account types**: 
       - Seleccionar "Accounts in this organizational directory only"
     - **Redirect URI**: (dejar en blanco por ahora)
   - Clic en "Register"

3. **Copiar Identificadores**
   Después del registro, copiar desde la página Overview:
   - **Application (client) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
   - **Directory (tenant) ID**: `yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy`

### 2.2 Crear Client Secret

1. **Generar Secret**
   - Menú lateral: "Certificates & secrets"
   - Pestaña "Client secrets" → "+ New client secret"
   - Configurar:
     - **Description**: `BV-Time-Logger-Secret`
     - **Expires**: 180 días (6 meses) o según política
   - Clic en "Add"

2. **Copiar Secret Value**
   - **COPIAR EL VALUE INMEDIATAMENTE** (no se podrá ver después)
   - ⚠️ **Nunca copiar el "Secret ID"**, solo el "Value"
   - Guardar temporalmente en un lugar seguro

### 2.3 Configurar Permisos de API

1. **Agregar Permisos**
   - Menú lateral: "API permissions"
   - Clic en "+ Add a permission"
   - Seleccionar "Microsoft Graph"

2. **Seleccionar Permisos de Aplicación**
   - Pestaña: "Application permissions" (NO "Delegated permissions")
   - Buscar y agregar:
     - ✅ **Calendars.Read**
     - ✅ **User.Read.All**
   - Clic en "Add permissions"

3. **Otorgar Consentimiento de Administrador**
   - En la página "API permissions"
   - Clic en "✓ Grant admin consent for {organización}"
   - Confirmar
   - ⚠️ **Crítico**: Sin este paso, la aplicación no funcionará

4. **Verificar Estado**
   - Todos los permisos deben mostrar:
     - Status: ✅ "Granted for {organización}"

### 2.4 Notas de Seguridad

- Los permisos de tipo **Application** permiten acceder a datos sin un usuario conectado
- Ideal para servicios automatizados/daemons
- Requiere consentimiento de administrador global

---

## 3. Configuración del Archivo .env

### 3.1 Editar .env

Abrir el archivo `.env` (creado desde `.env.template`) y configurar:

```bash
# ====================================
# Azure DevOps Configuration
# ====================================
AZURE_DEVOPS_ORGANIZATION=tu-organizacion
AZURE_DEVOPS_PAT=tu-pat-de-52-caracteres
AZURE_DEVOPS_PROJECT=nombre-del-proyecto

# ====================================
# Azure AD / Microsoft Graph Configuration
# ====================================
AZURE_AD_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_AD_CLIENT_SECRET=tu-client-secret-valor
AZURE_AD_TENANT_ID=yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy

# ====================================
# Application Settings
# ====================================
LOG_LEVEL=INFO
TIME_ZONE=America/Bogota
```

### 3.2 Ejemplo de Valores

```bash
# Ejemplo (NO USAR ESTOS VALORES REALES)
AZURE_DEVOPS_ORGANIZATION=bigview-sas
AZURE_DEVOPS_PAT=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
AZURE_DEVOPS_PROJECT=BV-Time-Logger

AZURE_AD_CLIENT_ID=12345678-1234-1234-1234-123456789abc
AZURE_AD_CLIENT_SECRET=AbC~1234567890_xYz-1234567890
AZURE_AD_TENANT_ID=87654321-4321-4321-4321-cba987654321

LOG_LEVEL=DEBUG
TIME_ZONE=America/Bogota
```

### 3.3 Verificar .gitignore

⚠️ **CRÍTICO**: Asegurar que `.env` está en `.gitignore`:

```bash
# Verificar
Get-Content .gitignore | Select-String ".env"

# Debe aparecer:
# .env
# .env.local
```

---

## 4. Validación de Accesos

### 4.1 Ejecutar Script de Validación

```powershell
# Activar entorno virtual
.\venv\Scripts\Activate.ps1

# Ejecutar validación
python validate_access.py
```

### 4.2 Salida Esperada

```
************************************************************
  BV-Time-Logger - Access Validation Script
************************************************************

============================================================
🔍 Validating Azure DevOps Access
============================================================
Organization: bigview-sas
Project: BV-Time-Logger
PAT: ************************************y5z6

📡 Testing connection to: https://dev.azure.com/bigview-sas/_apis/projects
✅ Azure DevOps connection successful!
   Found 3 project(s)

   Available projects:
   - BV-Time-Logger
   - Internal-Tools
   - Client-Portal

============================================================
🔍 Validating Microsoft Graph Access
============================================================
Tenant ID: 87654321-4321-4321-4321-cba987654321
Client ID: 12345678-1234-1234-1234-123456789abc
Client Secret: ********

🔐 Acquiring token from: https://login.microsoftonline.com/87654321-...
✅ Microsoft Graph authentication successful!

📡 Testing Graph API call to /me endpoint
⚠️  Token acquired but /me endpoint failed (status: 401)
   This is normal for service principals without user context.
   Calendar access will work if permissions are correctly set.

============================================================
📋 Required Permissions Checklist
============================================================

✓ Azure DevOps PAT Requirements:
  - Work Items: Read & Write
  - Project and Team: Read

✓ Azure AD App Registration Requirements:
  - API Permissions:
    • Calendars.Read (Application)
    • User.Read.All (Application)
  - Admin consent granted for organization

Note: Ensure all permissions have admin consent granted.

============================================================
📊 Validation Summary
============================================================
  Azure DevOps: ✅ PASS
  Microsoft Graph: ✅ PASS

============================================================
🎉 All validations passed! You're ready to start development.
```

### 4.3 Solución de Problemas

#### Error: "Authentication failed. Check your PAT"
- Verificar que el PAT fue copiado correctamente
- Comprobar que no haya espacios adicionales
- Verificar fecha de expiración del PAT
- Regenerar PAT si es necesario

#### Error: "Failed to acquire token"
- Verificar Client ID, Client Secret y Tenant ID
- Asegurar que el Client Secret no haya expirado
- Verificar que los valores fueron copiados correctamente

#### Error: "Admin consent not granted"
- Ir a Azure Portal → App Registration → API permissions
- Clic en "Grant admin consent"
- Esperar unos segundos y volver a intentar

---

## 5. Próximos Pasos

Una vez que la validación sea exitosa:

1. ✅ **Fase 0 Completa**
2. 📝 Revisar [docs/03-PROJECT_PHASES.md](03-PROJECT_PHASES.md) para continuar con Fase 1
3. 🏗️ Comenzar implementación de módulos de autenticación

---

## 6. Recursos Adicionales

- [Azure DevOps REST API Documentation](https://learn.microsoft.com/rest/api/azure/devops/)
- [Microsoft Graph API Documentation](https://learn.microsoft.com/graph/api/overview)
- [MSAL Python Documentation](https://msal-python.readthedocs.io/)
- [Azure AD App Registration Guide](https://learn.microsoft.com/azure/active-directory/develop/quickstart-register-app)

---

## 7. Contacto y Soporte

Para problemas o preguntas sobre la configuración:
- Contactar al administrador de Azure de Bigview SAS
- Revisar [docs/00-TOC.md](00-TOC.md) para más documentación
- Abrir un issue en el repositorio
