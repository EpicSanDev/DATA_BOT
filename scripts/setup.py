#!/usr/bin/env python3
"""
Quick setup script for DATA_BOT
This script helps new users get started with the reorganized project structure.
"""

import os
import shutil
import sys
from pathlib import Path

def setup_environment():
    """Set up the environment for DATA_BOT"""
    print("🤖 Setting up DATA_BOT environment...")
    
    # Create necessary directories
    directories = [
        "archive", "screenshots", "logs", "data",
        "data/ml_models", "data/clustering_models", "data/vectors"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    # Copy environment configuration
    env_example = "config/.env.example"
    env_file = ".env"
    
    if os.path.exists(env_example) and not os.path.exists(env_file):
        shutil.copy(env_example, env_file)
        print(f"✅ Created {env_file} from template")
    
    print("\n📋 Next steps:")
    print("1. Edit .env file to configure your settings")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Run the application: python main.py")
    print("\n🎉 Setup complete!")

if __name__ == "__main__":
    setup_environment()