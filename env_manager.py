#!/usr/bin/env python3
"""
Environment management script for SmartBoy backend
"""

import os
import sys
import subprocess
import shutil

def set_environment(env_type):
    """Set the environment type and copy appropriate env file"""
    env_files = {
        'dev': '.env.development',
        'development': '.env.development',
        'prod': '.env.production',
        'production': '.env.production'
    }
    
    if env_type not in env_files:
        print(f"❌ Invalid environment: {env_type}")
        print("Available environments: dev/development, prod/production")
        return False
    
    source_file = env_files[env_type]
    target_file = '.env'
    
    if not os.path.exists(source_file):
        print(f"❌ Environment file not found: {source_file}")
        return False
    
    # Copy the environment file
    try:
        shutil.copy2(source_file, target_file)
        print(f"✅ Environment set to: {env_type}")
        print(f"📁 Copied {source_file} → {target_file}")
        
        # Set environment variable for current session
        os.environ['ENVIRONMENT'] = 'development' if env_type in ['dev', 'development'] else 'production'
        
        return True
    except Exception as e:
        print(f"❌ Failed to copy environment file: {e}")
        return False

def start_server(env_type='dev'):
    """Start the development server with specified environment"""
    if not set_environment(env_type):
        return
    
    print(f"\n🚀 Starting SmartBoy backend server in {env_type} mode...")
    
    # Determine server settings based on environment
    if env_type in ['dev', 'development']:
        host = "localhost"
        port = "8000"
        reload = "--reload"
        print(f"🔧 Development server: http://{host}:{port}")
        print("🔄 Auto-reload enabled")
    else:
        host = "0.0.0.0"
        port = "8000"
        reload = ""
        print(f"🔧 Production server: http://{host}:{port}")
        print("⚠️  Auto-reload disabled")
    
    # Start the server
    try:
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", host, 
            "--port", port
        ]
        if reload:
            cmd.append(reload)
        
        print(f"📡 Running: {' '.join(cmd)}")
        print("Press Ctrl+C to stop the server\n")
        
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")

def show_status():
    """Show current environment status"""
    print("📊 SmartBoy Backend Environment Status")
    print("=" * 40)
    
    # Check which environment is active
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            content = f.read()
            if 'ENVIRONMENT=development' in content:
                print("🔧 Current Environment: DEVELOPMENT")
                print("💾 Database: PostgreSQL (localhost:5432/smartboy_dev)")
                print("🌐 Host: localhost:8000")
            elif 'ENVIRONMENT=production' in content:
                print("🏭 Current Environment: PRODUCTION")
                print("💾 Database: Neon PostgreSQL (cloud)")
                print("🌐 Host: 0.0.0.0:8000")
            else:
                print("❓ Current Environment: UNKNOWN")
    else:
        print("❌ No environment configured (.env file missing)")
    
    print()
    print("Available commands:")
    print("  python env_manager.py dev     - Switch to development")
    print("  python env_manager.py prod    - Switch to production")
    print("  python env_manager.py start   - Start server (dev mode)")
    print("  python env_manager.py start prod - Start server (prod mode)")
    print("  python env_manager.py status  - Show this status")

def main():
    if len(sys.argv) < 2:
        show_status()
        return
    
    command = sys.argv[1].lower()
    
    if command in ['dev', 'development']:
        set_environment('development')
        
    elif command in ['prod', 'production']:
        set_environment('production')
        
    elif command == 'start':
        env_type = sys.argv[2] if len(sys.argv) > 2 else 'dev'
        start_server(env_type)
        
    elif command == 'status':
        show_status()
        
    else:
        print(f"❌ Unknown command: {command}")
        show_status()

if __name__ == '__main__':
    main()