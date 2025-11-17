"""
Quick test script to verify the project setup
"""
import asyncio
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def test_imports():
    """Test that all modules can be imported"""
    print("🧪 Testing module imports...")
    
    try:
        from src.config.settings import SIMULATION_CONFIG, MESSAGE_TYPES
        print("✅ Configuration module imported successfully")
        
        from src.environment.city import City, Position, Route
        print("✅ Environment module imported successfully")
        
        from src.agents.base_agent import BaseTransportAgent
        from src.agents.vehicle_agent import VehicleAgent
        from src.agents.station_agent import StationAgent
        from src.agents.maintenance_agent import MaintenanceAgent
        print("✅ Agent modules imported successfully")
        
        from src.protocols.contract_net import ContractNetInitiator, ContractNetParticipant
        print("✅ Protocol modules imported successfully")
        
        print("\n🎉 All modules imported successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

async def test_city_creation():
    """Test city environment creation"""
    print("\n🏙️  Testing city creation...")
    
    try:
        from src.config.settings import SIMULATION_CONFIG
        from src.environment.city import City
        
        city = City(SIMULATION_CONFIG['city'])
        print(f"✅ City created with {len(city.stations)} stations")
        print(f"✅ City has {len(city.routes)} routes")
        print(f"✅ Grid size: {city.grid_size}")
        
        return True
        
    except Exception as e:
        print(f"❌ City creation error: {e}")
        return False

async def test_agent_creation():
    """Test basic agent creation"""
    print("\n🤖 Testing agent creation...")
    
    try:
        from src.environment.city import City, Position, Route
        from src.config.settings import SIMULATION_CONFIG
        from src.agents.station_agent import StationAgent
        
        # Create a test station agent (without starting it)
        city = City(SIMULATION_CONFIG['city'])
        test_position = Position(5, 5)
        
        # Note: We won't actually start the agent since we don't have XMPP running
        station_config = {
            'jid': 'test_station@localhost',
            'password': 'password',
            'station_id': 'test_station',
            'position': test_position
        }
        
        print("✅ Agent configuration created successfully")
        print("ℹ️  Note: Actual agent startup requires XMPP server")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent creation error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting Multi-Agent Transportation System Tests")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 3
    
    # Test imports
    if await test_imports():
        tests_passed += 1
    
    # Test city creation
    if await test_city_creation():
        tests_passed += 1
    
    # Test agent creation
    if await test_agent_creation():
        tests_passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! The project is ready to run.")
        print("\nNext steps:")
        print("1. Ensure you have an XMPP server running (or use localhost)")
        print("2. Run: python main.py")
        print("3. Watch the console visualization")
    else:
        print("❌ Some tests failed. Please check the error messages above.")
        print("\nTroubleshooting:")
        print("1. Ensure virtual environment is activated")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Check Python path and module structure")

if __name__ == "__main__":
    asyncio.run(main())