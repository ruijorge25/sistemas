"""Test dashboard APIs"""
import requests
import json
import time

def test_apis():
    base_url = "http://localhost:8080"
    endpoints = [
        "/api/status",
        "/api/vehicles",
        "/api/stations",
        "/api/metrics",
        "/api/bases"
    ]
    
    print("🔍 Testing Dashboard APIs...\n")
    
    for endpoint in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {endpoint}")
                print(f"   Response: {json.dumps(data, indent=2)[:200]}...\n")
            else:
                print(f"❌ {endpoint} - Status: {response.status_code}\n")
        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}\n")
    
    print("\n✅ API tests completed!")

if __name__ == "__main__":
    print("Waiting for system to start...")
    time.sleep(5)
    test_apis()
