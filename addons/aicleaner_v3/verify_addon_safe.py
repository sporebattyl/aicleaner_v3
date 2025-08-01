#!/usr/bin/env python3
"""
AICleaner V3 Addon Verification Script
Checks if the addon repository is properly configured and accessible.
"""

import requests
import yaml
import json
import os
from pathlib import Path

def check_github_repo_accessible():
    """Check if the GitHub repository is accessible"""
    try:
        response = requests.get("https://api.github.com/repos/sporebattyl/aicleaner_v3")
        if response.status_code == 200:
            repo_data = response.json()
            print(f"✅ GitHub repository is accessible")
            print(f"   - Public: {not repo_data.get('private', True)}")
            print(f"   - Default branch: {repo_data.get('default_branch', 'N/A')}")
            return True
        else:
            print(f"❌ GitHub repository not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error accessing GitHub repository: {e}")
        return False

def check_repository_yaml():
    """Check repository.yaml configuration"""
    try:
        repo_yaml_path = Path(__file__).parent.parent / "repository.yaml"
        if not repo_yaml_path.exists():
            print("❌ repository.yaml not found")
            return False
            
        with open(repo_yaml_path, 'r') as f:
            repo_config = yaml.safe_load(f)
            
        print("✅ repository.yaml found and valid")
        print(f"   - Name: {repo_config.get('name', 'N/A')}")
        print(f"   - URL: {repo_config.get('url', 'N/A')}")
        print(f"   - Addons: {list(repo_config.get('addons', {}).keys())}")
        return True
    except Exception as e:
        print(f"❌ Error reading repository.yaml: {e}")
        return False

def check_addon_config():
    """Check addon config.yaml configuration"""
    try:
        config_path = Path(__file__).parent / "config.yaml"
        if not config_path.exists():
            print("❌ config.yaml not found")
            return False
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        print("✅ config.yaml found and valid")
        print(f"   - Name: {config.get('name', 'N/A')}")
        print(f"   - Version: {config.get('version', 'N/A')}")
        print(f"   - Slug: {config.get('slug', 'N/A')}")
        print(f"   - Image: {config.get('image', 'N/A')}")
        print(f"   - Architectures: {config.get('arch', [])}")
        return True
    except Exception as e:
        print(f"❌ Error reading config.yaml: {e}")
        return False

def check_docker_images():
    """Check if Docker images are accessible (requires GITHUB_TOKEN env var)"""
    try:
        token = os.environ.get('GITHUB_TOKEN')
        if not token:
            print("⚠️  GITHUB_TOKEN not set, skipping Docker image verification")
            print("   Run with GITHUB_TOKEN=your_token to verify Docker images")
            return True
            
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get("https://api.github.com/user/packages?package_type=container", headers=headers)
        
        if response.status_code == 200:
            packages = response.json()
            aicleaner_packages = [p for p in packages if 'aicleaner_v3' in p['name']]
            
            if aicleaner_packages:
                print("✅ Docker images are published")
                for package in aicleaner_packages:
                    print(f"   - {package['name']}")
                return True
            else:
                print("❌ No AICleaner V3 Docker images found")
                return False
        else:
            print(f"❌ Cannot access GitHub Container Registry: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking Docker images: {e}")
        return False

def test_raw_github_access():
    """Test if raw GitHub files are accessible"""
    try:
        # Test repository.yaml access
        repo_url = "https://raw.githubusercontent.com/sporebattyl/aicleaner_v3/main/repository.yaml"
        response = requests.get(repo_url)
        
        if response.status_code == 200:
            print("✅ repository.yaml accessible via raw GitHub")
        else:
            print(f"❌ repository.yaml not accessible: {response.status_code}")
            return False
        
        # Test config.yaml access
        config_url = "https://raw.githubusercontent.com/sporebattyl/aicleaner_v3/main/aicleaner_v3/config.yaml"
        response = requests.get(config_url)
        
        if response.status_code == 200:
            print("✅ config.yaml accessible via raw GitHub")
            return True
        else:
            print(f"❌ config.yaml not accessible: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing raw GitHub access: {e}")
        return False

def main():
    print("🔍 AICleaner V3 Addon Verification")
    print("=" * 50)
    
    checks = [
        ("GitHub Repository Access", check_github_repo_accessible),
        ("Repository Configuration", check_repository_yaml),
        ("Addon Configuration", check_addon_config),
        ("Raw GitHub File Access", test_raw_github_access),
        ("Docker Images", check_docker_images)
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"\n📋 Checking {name}...")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All checks passed! The addon should be discoverable in Home Assistant.")
        print("\nTo add the repository to Home Assistant:")
        print("1. Go to Settings > Add-ons > Add-on Store")
        print("2. Click the 3-dot menu in the top right")
        print("3. Select 'Repositories'")
        print("4. Add: https://github.com/sporebattyl/aicleaner_v3")
        print("5. Look for 'AICleaner V3' in the addon store")
    else:
        print("❌ Some checks failed. Please review the issues above.")
    
    return all_passed

if __name__ == "__main__":
    main()