"""Test API endpoints quickly"""
import sys
import time
import subprocess
import requests

def test_endpoint(url):
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            data = r.json()
            print(f"✅ {url}")
            print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, list):
                        print(f"   - {k}: {len(v)} items")
                    else:
                        print(f"   - {k}: {v}")
            elif isinstance(data, list):
                print(f"   - Total items: {len(data)}")
                if len(data) > 0:
                    print(f"   - First item keys: {list(data[0].keys())}")
            return True
        else:
            print(f"❌ {url} - Status {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ {url} - {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing Dashboard APIs...\n")
    print("Waiting 3 seconds for system to start...\n")
    time.sleep(3)
    
    endpoints = [
        "http://localhost:8080/api/status",
        "http://localhost:8080/api/vehicles",
        "http://localhost:8080/api/stations",
        "http://localhost:8080/api/metrics",
        "http://localhost:8080/api/bases"
    ]
    
    for url in endpoints:
        test_endpoint(url)
        print()
