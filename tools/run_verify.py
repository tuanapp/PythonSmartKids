import os
import sys
from pathlib import Path

# Add the current directory to path so we can import diagnose_service_account
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

import diagnose_service_account

def load_env_and_run():
    # Find .env file
    env_path = current_dir.parent / '.env'
    print(f"Looking for .env at: {env_path}")
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip().startswith('GOOGLE_PLAY_SERVICE_ACCOUNT_JSON='):
                    # Split on first = only
                    key = line.strip().split('=', 1)[1]
                    os.environ['GOOGLE_PLAY_SERVICE_ACCOUNT_JSON'] = key.strip()
                    print("✅ Loaded GOOGLE_PLAY_SERVICE_ACCOUNT_JSON from .env")
                    break
    else:
        print("❌ .env file not found")
        return

    # Run the main function from the diagnostic tool
    diagnose_service_account.main()

if __name__ == "__main__":
    load_env_and_run()
