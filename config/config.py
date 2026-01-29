"""
Configuration module for BV-Time-Logger
Loads environment variables and provides configuration settings
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Application configuration from environment variables"""
    
    # Azure DevOps Configuration
    AZURE_DEVOPS_ORGANIZATION: str = os.getenv('AZURE_DEVOPS_ORGANIZATION', '')
    AZURE_DEVOPS_PROJECT: str = os.getenv('AZURE_DEVOPS_PROJECT', '')
    AZURE_DEVOPS_PAT: str = os.getenv('AZURE_DEVOPS_PAT', '')
    AZURE_DEVOPS_API_VERSION: str = '7.1'
    
    # Microsoft Graph API Configuration
    AZURE_AD_CLIENT_ID: str = os.getenv('AZURE_AD_CLIENT_ID', '')
    AZURE_AD_CLIENT_SECRET: str = os.getenv('AZURE_AD_CLIENT_SECRET', '')
    AZURE_AD_TENANT_ID: str = os.getenv('AZURE_AD_TENANT_ID', '')
    GRAPH_API_ENDPOINT: str = 'https://graph.microsoft.com/v1.0'
    
    # Application Settings
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    TIMEZONE: str = os.getenv('TIMEZONE', 'America/Bogota')
    SYNC_FREQUENCY_HOURS: int = int(os.getenv('SYNC_FREQUENCY_HOURS', '24'))
    SYNC_DAILY_TIME: str = os.getenv('SYNC_DAILY_TIME', '00:00')
    
    # Optional: Azure Key Vault
    AZURE_KEY_VAULT_URL: Optional[str] = os.getenv('AZURE_KEY_VAULT_URL')
    
    # Optional: Email Configuration
    SMTP_SERVER: Optional[str] = os.getenv('SMTP_SERVER')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME: Optional[str] = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD: Optional[str] = os.getenv('SMTP_PASSWORD')
    REPORT_RECIPIENTS: Optional[str] = os.getenv('REPORT_RECIPIENTS')
    
    # Optional: Database
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', './data/timetracker.db')
    
    # Development/Testing
    DRY_RUN: bool = os.getenv('DRY_RUN', 'false').lower() == 'true'
    TEST_USER_EMAIL: Optional[str] = os.getenv('TEST_USER_EMAIL')
    
    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate that all required configuration is present
        
        Returns:
            tuple[bool, list[str]]: (is_valid, list_of_errors)
        """
        errors = []
        
        # Required Azure DevOps settings
        if not cls.AZURE_DEVOPS_ORGANIZATION:
            errors.append("AZURE_DEVOPS_ORGANIZATION no está configurado")
        if not cls.AZURE_DEVOPS_PROJECT:
            errors.append("AZURE_DEVOPS_PROJECT no está configurado")
        if not cls.AZURE_DEVOPS_PAT:
            errors.append("AZURE_DEVOPS_PAT no está configurado")
        
        # Required Azure AD settings
        if not cls.AZURE_AD_CLIENT_ID:
            errors.append("AZURE_AD_CLIENT_ID no está configurado")
        if not cls.AZURE_AD_CLIENT_SECRET:
            errors.append("AZURE_AD_CLIENT_SECRET no está configurado")
        if not cls.AZURE_AD_TENANT_ID:
            errors.append("AZURE_AD_TENANT_ID no está configurado")
        
        return (len(errors) == 0, errors)
    
    @classmethod
    def get_devops_base_url(cls) -> str:
        """Get base URL for Azure DevOps API"""
        return f"https://dev.azure.com/{cls.AZURE_DEVOPS_ORGANIZATION}"
    
    @classmethod
    def get_authority_url(cls) -> str:
        """Get Azure AD authority URL"""
        return f"https://login.microsoftonline.com/{cls.AZURE_AD_TENANT_ID}"
    
    @classmethod
    def get_report_recipients(cls) -> list[str]:
        """Get list of email recipients for reports"""
        if not cls.REPORT_RECIPIENTS:
            return []
        return [email.strip() for email in cls.REPORT_RECIPIENTS.split(',')]
    
    @classmethod
    def is_email_configured(cls) -> bool:
        """Check if email notifications are configured"""
        return all([
            cls.SMTP_SERVER,
            cls.SMTP_USERNAME,
            cls.SMTP_PASSWORD,
            cls.REPORT_RECIPIENTS
        ])
    
    @classmethod
    def print_config(cls, hide_secrets: bool = True) -> None:
        """
        Print current configuration (for debugging)
        
        Args:
            hide_secrets: If True, mask sensitive values
        """
        print("=" * 60)
        print("BV-Time-Logger Configuration")
        print("=" * 60)
        
        def mask(value: str) -> str:
            """Mask sensitive values"""
            if not value or not hide_secrets:
                return value
            if len(value) <= 8:
                return "*" * len(value)
            return value[:4] + "*" * (len(value) - 8) + value[-4:]
        
        print(f"\nAzure DevOps:")
        print(f"  Organization: {cls.AZURE_DEVOPS_ORGANIZATION}")
        print(f"  Project: {cls.AZURE_DEVOPS_PROJECT}")
        print(f"  PAT: {mask(cls.AZURE_DEVOPS_PAT)}")
        
        print(f"\nMicrosoft Graph API:")
        print(f"  Client ID: {mask(cls.AZURE_AD_CLIENT_ID)}")
        print(f"  Tenant ID: {cls.AZURE_AD_TENANT_ID}")
        print(f"  Client Secret: {mask(cls.AZURE_AD_CLIENT_SECRET)}")
        
        print(f"\nApplication Settings:")
        print(f"  Log Level: {cls.LOG_LEVEL}")
        print(f"  Timezone: {cls.TIMEZONE}")
        print(f"  Sync Frequency: Every {cls.SYNC_FREQUENCY_HOURS} hours")
        print(f"  Daily Sync Time: {cls.SYNC_DAILY_TIME}")
        print(f"  Dry Run: {cls.DRY_RUN}")
        
        if cls.is_email_configured():
            print(f"\nEmail Configuration:")
            print(f"  SMTP Server: {cls.SMTP_SERVER}:{cls.SMTP_PORT}")
            print(f"  Recipients: {len(cls.get_report_recipients())} configured")
        
        print("=" * 60)


# Validate configuration on import
is_valid, validation_errors = Config.validate()

if not is_valid:
    print("\n⚠️  ADVERTENCIA: Configuración incompleta")
    print("Errores encontrados:")
    for error in validation_errors:
        print(f"  - {error}")
    print("\nPor favor, revisa tu archivo .env")
    print("Usa .env.template como referencia\n")
