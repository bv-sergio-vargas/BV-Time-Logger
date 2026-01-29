# 🚀 Inicio Rápido - BV-Time-Logger

## ⚡ Empezar en 15 Minutos

### Prerequisitos
- Python 3.9+
- Cuenta de Azure DevOps
- Cuenta de Microsoft 365 con Teams
- Git

---

## Paso 1: Clonar y Configurar Entorno (5 min)

```powershell
# Clonar repositorio (si aún no lo has hecho)
cd c:\github-sv\BV-Time-Logger

# Crear entorno virtual
python -m venv venv

# Activar entorno
venv\Scripts\activate

# Instalar dependencias básicas
pip install msal requests python-dotenv apscheduler

# Guardar dependencias
pip freeze > requirements.txt
```

---

## Paso 2: Crear Estructura de Proyecto (2 min)

```powershell
# Crear carpetas
mkdir src\auth, src\clients, src\core, src\reports, src\utils, tests, docs, config

# Crear archivos iniciales
New-Item -ItemType File -Path "src\__init__.py"
New-Item -ItemType File -Path "src\auth\__init__.py"
New-Item -ItemType File -Path "src\clients\__init__.py"
New-Item -ItemType File -Path "src\core\__init__.py"
New-Item -ItemType File -Path "src\reports\__init__.py"
New-Item -ItemType File -Path "src\utils\__init__.py"
New-Item -ItemType File -Path "tests\__init__.py"
New-Item -ItemType File -Path ".env"
New-Item -ItemType File -Path "src\main.py"
```

---

## Paso 3: Configurar Accesos Azure (5 min)

### 3.1 Azure DevOps - Personal Access Token (PAT)

1. Ir a: https://dev.azure.com/{tu-organization}/_usersSettings/tokens
2. Click en "New Token"
3. Configurar:
   - **Name**: BV-Time-Logger
   - **Organization**: Tu organización
   - **Expiration**: 90 días (o Custom)
   - **Scopes**: 
     - ✅ Work Items (Read & Write)
     - ✅ Project and Team (Read)
4. Click "Create" y **copiar el token** (no se podrá ver de nuevo)

### 3.2 Azure AD - Registro de Aplicación

1. Ir a: https://portal.azure.com/#blade/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/RegisteredApps
2. Click "New registration"
3. Configurar:
   - **Name**: BV-Time-Logger
   - **Supported account types**: Single tenant
   - **Redirect URI**: Web - `http://localhost:8000/callback`
4. Click "Register"
5. En la página de la app:
   - Copiar **Application (client) ID**
   - Copiar **Directory (tenant) ID**
6. Ir a "Certificates & secrets"
   - Click "New client secret"
   - Description: "BV-Time-Logger Secret"
   - Expires: 24 months
   - Click "Add" y **copiar el Value**
7. Ir a "API permissions"
   - Click "Add a permission"
   - Seleccionar "Microsoft Graph"
   - "Application permissions"
   - Buscar y agregar:
     - ✅ `Calendars.Read`
     - ✅ `User.Read.All`
   - Click "Grant admin consent" (requiere admin)

---

## Paso 4: Configurar Variables de Entorno (2 min)

Editar archivo `.env`:

```env
# Azure DevOps Configuration
AZURE_DEVOPS_ORGANIZATION=tu-organizacion
AZURE_DEVOPS_PROJECT=tu-proyecto
AZURE_DEVOPS_PAT=tu-personal-access-token-aqui

# Microsoft Graph API Configuration
AZURE_AD_CLIENT_ID=tu-client-id-aqui
AZURE_AD_CLIENT_SECRET=tu-client-secret-aqui
AZURE_AD_TENANT_ID=tu-tenant-id-aqui

# Application Configuration
LOG_LEVEL=INFO
TIMEZONE=America/Bogota
```

⚠️ **IMPORTANTE**: Asegúrate de que `.env` esté en `.gitignore`

---

## Paso 5: Primer Test de Conexión (1 min)

Crear archivo `src/test_connection.py`:

```python
import os
from dotenv import load_dotenv
import requests
from msal import ConfidentialClientApplication

# Cargar variables de entorno
load_dotenv()

def test_azure_devops():
    """Test de conexión a Azure DevOps"""
    org = os.getenv('AZURE_DEVOPS_ORGANIZATION')
    pat = os.getenv('AZURE_DEVOPS_PAT')
    
    url = f"https://dev.azure.com/{org}/_apis/projects?api-version=7.1"
    
    response = requests.get(
        url,
        auth=('', pat),
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        print("✅ Azure DevOps: Conexión exitosa")
        projects = response.json()
        print(f"   Proyectos encontrados: {projects['count']}")
        for project in projects['value'][:3]:
            print(f"   - {project['name']}")
        return True
    else:
        print(f"❌ Azure DevOps: Error {response.status_code}")
        print(f"   {response.text}")
        return False

def test_microsoft_graph():
    """Test de conexión a Microsoft Graph API"""
    client_id = os.getenv('AZURE_AD_CLIENT_ID')
    client_secret = os.getenv('AZURE_AD_CLIENT_SECRET')
    tenant_id = os.getenv('AZURE_AD_TENANT_ID')
    
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    scopes = ["https://graph.microsoft.com/.default"]
    
    app = ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority
    )
    
    result = app.acquire_token_for_client(scopes=scopes)
    
    if "access_token" in result:
        print("✅ Microsoft Graph: Autenticación exitosa")
        
        # Test API call
        headers = {'Authorization': f'Bearer {result["access_token"]}'}
        response = requests.get(
            'https://graph.microsoft.com/v1.0/users?$top=1',
            headers=headers
        )
        
        if response.status_code == 200:
            print("   API funcionando correctamente")
            return True
        else:
            print(f"   ⚠️  API Error: {response.status_code}")
            return False
    else:
        print("❌ Microsoft Graph: Error de autenticación")
        print(f"   {result.get('error_description', 'Error desconocido')}")
        return False

if __name__ == "__main__":
    print("🔍 Probando conexiones...\n")
    
    devops_ok = test_azure_devops()
    print()
    graph_ok = test_microsoft_graph()
    
    print("\n" + "="*50)
    if devops_ok and graph_ok:
        print("✅ Todas las conexiones funcionan correctamente")
        print("🚀 Listo para comenzar el desarrollo!")
    else:
        print("⚠️  Algunas conexiones fallaron")
        print("📝 Verifica tu configuración en .env")
```

### Ejecutar el test:

```powershell
python src/test_connection.py
```

Deberías ver:
```
✅ Azure DevOps: Conexión exitosa
   Proyectos encontrados: 3
   - Proyecto 1
   - Proyecto 2
   - Proyecto 3

✅ Microsoft Graph: Autenticación exitosa
   API funcionando correctamente

==================================================
✅ Todas las conexiones funcionan correctamente
🚀 Listo para comenzar el desarrollo!
```

---

## ✅ Checklist de Configuración Inicial

- [ ] Python 3.9+ instalado
- [ ] Entorno virtual creado y activado
- [ ] Dependencias instaladas
- [ ] Estructura de carpetas creada
- [ ] Azure DevOps PAT generado
- [ ] Azure AD App registrada
- [ ] Archivo `.env` configurado
- [ ] Test de conexiones exitoso

---

## 📚 Próximos Pasos

Una vez completada la configuración inicial:

1. **Leer el documento de fases**: [03-PROJECT_PHASES.md](03-PROJECT_PHASES.md)
2. **Comenzar Fase 1**: Implementar módulos de autenticación
3. **Revisar requerimientos**: [02-REQUIREMENTS.md](02-REQUIREMENTS.md)

---

## 🆘 Troubleshooting

### Error: "Invalid PAT"
- Verifica que el PAT no haya expirado
- Confirma que los permisos incluyan Work Items (Read & Write)
- Asegúrate de que no haya espacios extra en el `.env`

### Error: "AADSTS700016: Application not found"
- Verifica el `AZURE_AD_CLIENT_ID`
- Confirma que la app esté registrada en el tenant correcto

### Error: "Forbidden" en Graph API
- Verifica que los permisos estén configurados
- Confirma que se haya dado "Admin consent"
- Espera 5-10 minutos después de dar el consent

### Error: Import msal not found
```powershell
venv\Scripts\activate
pip install msal
```

---

## 📞 Soporte

- **Documentación completa**: [00-TOC.md](00-TOC.md)
- **Fases del proyecto**: [03-PROJECT_PHASES.md](03-PROJECT_PHASES.md)
- **Requerimientos**: [02-REQUIREMENTS.md](02-REQUIREMENTS.md)
- **Issues**: Reportar en GitHub Issues

---

## 🎯 Objetivo del Proyecto

Automatizar el registro de horas trabajadas sincronizando:
- ⏰ Reuniones de Microsoft Teams → Tiempo real invertido
- 📋 Work Items de Azure DevOps → Tiempo estimado
- 📊 Generar reportes de discrepancias
- 🔄 Actualizar automáticamente las horas completadas

**¡Comencemos! 🚀**
