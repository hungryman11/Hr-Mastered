import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv('ZOHO_CLIENT_ID')
CLIENT_SECRET = os.getenv('ZOHO_CLIENT_SECRET')
# Make sure this redirect URI matches EXACTLY what is registered in Zoho Developer Console
REDIRECT_URI = 'http://localhost:8000/zoho/oauth/callback'
ACCOUNTS_URL = os.getenv('ZOHO_ACCOUNTS_URL', 'https://accounts.zoho.com').rstrip('/')

def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: ZOHO_CLIENT_ID or ZOHO_CLIENT_SECRET is missing from your .env file.")
        return

    # Scopes needed for WorkDrive operations
    scopes = "WorkDrive.files.ALL"
    
    # 1. Generate authorization URL
    auth_url = (
        f"{ACCOUNTS_URL}/oauth/v2/auth"
        f"?scope={scopes}"
        f"&client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&access_type=offline"  # Offline access is required to get a refresh token!
        f"&prompt=consent"
        f"&redirect_uri={REDIRECT_URI}"
    )
    
    print("\n=== Zoho OAuth 2.0 Refresh Token Helper ===\n")
    print("Step 1: Open the following URL in your web browser and authorize access:")
    print("-" * 80)
    print(auth_url)
    print("-" * 80)
    print("\nStep 2: After authorizing, you will be redirected to your Redirect URI.")
    print("   Look at the browser URL bar and copy the value of the 'code' parameter.")
    print("   Example URL: http://localhost:8000/zoho/oauth/callback?code=1000.xxxxxx.xxxxxx")
    
    code = input("\nEnter the authorization code: ").strip()
    if not code:
        print("Error: Authorization code cannot be empty.")
        return
        
    # Auto-extract code if the user pasted the entire redirect URL
    if 'code=' in code:
        code = code.split('code=')[1].split('&')[0]

    # 2. Exchange authorization code for tokens
    token_url = f"{ACCOUNTS_URL}/oauth/v2/token"
    payload = {
        'code': code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code',
    }
    
    print(f"\nExchanging authorization code on {token_url}...")
    try:
        response = requests.post(token_url, data=payload)
        response.raise_for_status()
        data = response.json()
        
        refresh_token = data.get('refresh_token')
        access_token = data.get('access_token')
        
        if not refresh_token:
            print("\nWarning: No refresh token returned. Did you already exchange this code or authorize previously?")
            print("Response details:", data)
            return
            
        print("\nSUCCESS!")
        print("=" * 60)
        print(f"ZOHO_REFRESH_TOKEN={refresh_token}")
        print("=" * 60)
        print("\nNext step: Copy the ZOHO_REFRESH_TOKEN line above and paste it into your .env file!")
        
    except Exception as e:
        print("\nError performing token exchange:", str(e))
        if hasattr(e, 'response') and e.response is not None:
            print("Response:", e.response.text)

if __name__ == '__main__':
    main()
