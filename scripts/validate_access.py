"""
BV-Time-Logger - Validation Script
Validates access to Azure DevOps and Microsoft Graph APIs
"""

import os
import sys
import requests
from dotenv import load_dotenv
import msal

# Load environment variables
load_dotenv()

# Configure stdout encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def print_section(title):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print('='*60)


def validate_azure_devops():
    """Validate Azure DevOps PAT and access"""
    print_section("[VALIDATION] Azure DevOps Access")
    
    organization = os.getenv('AZURE_DEVOPS_ORGANIZATION')
    pat = os.getenv('AZURE_DEVOPS_PAT')
    project = os.getenv('AZURE_DEVOPS_PROJECT')
    
    if not organization or not pat:
        print(f"{RED}[ERROR] Missing Azure DevOps configuration in .env{RESET}")
        print(f"   Required: AZURE_DEVOPS_ORGANIZATION, AZURE_DEVOPS_PAT")
        return False
    
    print(f"Organization: {organization}")
    print(f"Project: {project if project else 'Not specified'}")
    print(f"PAT: {'*' * (len(pat) - 4)}{pat[-4:]}")
    
    # Test connection to Azure DevOps API
    try:
        url = f"https://dev.azure.com/{organization}/_apis/projects?api-version=7.1"
        
        import base64
        pat_bytes = f":{pat}".encode('ascii')
        b64_pat = base64.b64encode(pat_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {b64_pat}',
            'Content-Type': 'application/json'
        }
        
        print(f"\n[INFO] Testing connection to: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            projects = response.json().get('value', [])
            print(f"{GREEN}[SUCCESS] Azure DevOps connection successful{RESET}")
            print(f"   Found {len(projects)} project(s)")
            
            if projects:
                print("\n   Available projects:")
                for proj in projects[:5]:  # Show first 5
                    print(f"   - {proj.get('name')}")
            
            return True
        elif response.status_code == 401:
            print(f"{RED}[ERROR] Authentication failed. Check your PAT.{RESET}")
            return False
        else:
            print(f"{RED}[ERROR] API error: {response.status_code}{RESET}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"{RED}[ERROR] Connection error: {str(e)}{RESET}")
        return False


def validate_microsoft_graph():
    """Validate Microsoft Graph API access"""
    print_section("[VALIDATION] Microsoft Graph Access")
    
    client_id = os.getenv('AZURE_AD_CLIENT_ID')
    client_secret = os.getenv('AZURE_AD_CLIENT_SECRET')
    tenant_id = os.getenv('AZURE_AD_TENANT_ID')
    
    if not all([client_id, client_secret, tenant_id]):
        print(f"{RED}[ERROR] Missing Microsoft Graph configuration in .env{RESET}")
        print(f"   Required: AZURE_AD_CLIENT_ID, AZURE_AD_CLIENT_SECRET, AZURE_AD_TENANT_ID")
        return False
    
    print(f"Tenant ID: {tenant_id}")
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {'*' * 8}")
    
    try:
        # Create MSAL confidential client
        authority = f"https://login.microsoftonline.com/{tenant_id}"
        app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=authority
        )
        
        print(f"\n[INFO] Acquiring token from: {authority}")
        
        # Get token
        scopes = ["https://graph.microsoft.com/.default"]
        result = app.acquire_token_for_client(scopes=scopes)
        
        if "access_token" in result:
            print(f"{GREEN}[SUCCESS] Microsoft Graph authentication successful{RESET}")
            
            # Test Graph API call
            token = result['access_token']
            headers = {'Authorization': f'Bearer {token}'}
            
            print(f"\n[INFO] Testing Graph API call to /me endpoint")
            graph_url = "https://graph.microsoft.com/v1.0/me"
            response = requests.get(graph_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_info = response.json()
                print(f"{GREEN}[SUCCESS] Graph API call successful{RESET}")
                print(f"   User: {user_info.get('displayName', 'N/A')}")
                print(f"   Email: {user_info.get('mail', user_info.get('userPrincipalName', 'N/A'))}")
            else:
                print(f"{YELLOW}[WARNING] Token acquired but /me endpoint failed (status: {response.status_code}){RESET}")
                print(f"   This is normal for service principals without user context.")
                print(f"   Calendar access will work if permissions are correctly set.")
            
            return True
        else:
            print(f"{RED}[ERROR] Failed to acquire token{RESET}")
            error_desc = result.get("error_description", "Unknown error")
            print(f"   Error: {error_desc}")
            return False
            
    except Exception as e:
        print(f"{RED}[ERROR] {str(e)}{RESET}")
        return False


def check_required_permissions():
    """Display required permissions checklist"""
    print_section("[CHECKLIST] Required Permissions")
    
    print("\n[+] Azure DevOps PAT Requirements:")
    print("  - Work Items: Read & Write")
    print("  - Project and Team: Read")
    
    print("\n[+] Azure AD App Registration Requirements:")
    print("  - API Permissions:")
    print("    - Calendars.Read (Application)")
    print("    - User.Read.All (Application)")
    print("  - Admin consent granted for organization")
    
    print(f"\n{YELLOW}[NOTE] Ensure all permissions have admin consent granted.{RESET}")


def main():
    """Main validation function"""
    print(f"\n{'*'*60}")
    print("  BV-Time-Logger - Access Validation Script")
    print(f"{'*'*60}")
    
    # Check if .env exists
    if not os.path.exists('.env'):
        print(f"\n{RED}[ERROR] .env file not found{RESET}")
        print(f"   Please copy .env.template to .env and configure your credentials.")
        sys.exit(1)
    
    results = []
    
    # Run validations
    results.append(("Azure DevOps", validate_azure_devops()))
    results.append(("Microsoft Graph", validate_microsoft_graph()))
    
    # Display checklist
    check_required_permissions()
    
    # Summary
    print_section("[SUMMARY] Validation Results")
    
    all_passed = all(result[1] for result in results)
    
    for service, passed in results:
        status = f"{GREEN}[PASS]{RESET}" if passed else f"{RED}[FAIL]{RESET}"
        print(f"  {service}: {status}")
    
    print("\n" + "="*60)
    
    if all_passed:
        print(f"{GREEN}[SUCCESS] All validations passed. Ready to start development.{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}[WARNING] Some validations failed. Please check the configuration.{RESET}")
        print(f"\nNext steps:")
        print(f"1. Review the error messages above")
        print(f"2. Check your .env configuration")
        print(f"3. Verify permissions in Azure portal")
        print(f"4. Consult docs/01-QUICKSTART.md for detailed setup instructions")
        sys.exit(1)


if __name__ == "__main__":
    main()
