"""
Main entry point - Real SPADE Multi-Agent System with Dashboard
Requires XMPP server running on localhost:5222
"""
import asyncio
from aiohttp import web
import json
from src.environment.city import City, Route, Position
from src.config.settings import SIMULATION_CONFIG
from src.agents.vehicle_agent import VehicleAgent
from src.agents.station_agent import StationAgent
from src.agents.passenger_agent import PassengerAgent
from src.agents.maintenance_agent import MaintenanceAgent
from src.metrics.collector import MetricsCollector
from src.environment.events import EventManager, EventScheduler
import random
import time

class SPADEDashboardServer:
    """Dashboard server that monitors real SPADE agents"""
    def __init__(self, city, agents_registry, metrics_collector, port=8080):
        self.city = city
        self.agents_registry = agents_registry  # Dict of all SPADE agents
        self.metrics_collector = metrics_collector
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        self.simulation_time = 0
        self.start_time = time.time()
    
    def get_real_vehicle_data(self):
        """Get data from real SPADE vehicle agents"""
        vehicles = []
        for agent_id, agent in self.agents_registry.items():
            if 'vehicle' in agent_id and hasattr(agent, 'current_position'):
                vehicles.append({
                    'id': agent.vehicle_id,
                    'type': agent.vehicle_type,
                    'position': [agent.current_position.x, agent.current_position.y],
                    'capacity': agent.capacity,
                    'passengers': len(agent.passengers),
                    'fuel': agent.fuel_level,
                    'status': 'broken' if agent.is_broken else 'active'
                })
        return vehicles
    
    def get_real_station_data(self):
        """Get data from real SPADE station agents"""
        stations = []
        for agent_id, agent in self.agents_registry.items():
            if 'station' in agent_id and hasattr(agent, 'position'):
                stations.append({
                    'name': agent.station_id,
                    'position': [agent.position.x, agent.position.y],
                    'waiting_passengers': len(agent.passenger_queue),
                    'predicted_demand': getattr(agent, 'predicted_demand', 0)
                })
        return stations
    
    def calculate_real_metrics(self):
        """Calculate metrics from real SPADE agents - USING MetricsCollector"""
        return self.metrics_collector.get_current_performance_summary(self.agents_registry)
    
    def setup_routes(self):
        """Setup web routes"""
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/api/status', self.api_status)
        self.app.router.add_get('/api/vehicles', self.api_vehicles)
        self.app.router.add_get('/api/stations', self.api_stations)
        self.app.router.add_get('/api/metrics', self.api_metrics)
    
    async def index(self, request):
        """Serve advanced dashboard"""
        import os
        template_path = os.path.join(os.path.dirname(__file__), 'src', 'visualization', 'templates', 'dashboard_advanced.html')
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                html = f.read()
            return web.Response(text=html, content_type='text/html')
        except FileNotFoundError:
            return web.Response(text="<h1>Dashboard not found</h1>", content_type='text/html')
    
    async def api_status(self, request):
        """API: System status"""
        return web.json_response({
            'status': 'running',
            'simulation_time': self.simulation_time,
            'total_vehicles': len(self.vehicles),
            'total_stations': len(self.city.stations)
        })
    
    async def api_vehicles(self, request):
        """API: Vehicle data from real SPADE agents"""
        return web.json_response(self.get_real_vehicle_data())
    
    async def api_stations(self, request):
        """API: Station data from real SPADE agents"""
        return web.json_response(self.get_real_station_data())
    
    async def api_metrics(self, request):
        """API: Performance metrics from real SPADE agents"""
        return web.json_response(self.calculate_real_metrics())
    
    async def update_simulation(self):
        """Update simulation time counter"""
        while True:
            await asyncio.sleep(2)
            self.simulation_time = int(time.time() - self.start_time)
    
    async def start(self):
        """Start the dashboard server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        print(f"🌐 Dashboard running at http://localhost:{self.port}")
        
        # Start simulation update loop
        asyncio.create_task(self.update_simulation())

async def create_spade_agents(city):
    """Create and start real SPADE agents"""
    agents = {}
    
    print("🤖 Creating SPADE agents...")
    
    # XMPP server configuration
    xmpp_server = "localhost"
    xmpp_domain = "@localhost"
    password = "password"
    
    # Create Station Agents
    for i, station_pos in enumerate(city.stations[:15]):
        jid = f"station{i}{xmpp_domain}"
        agent = StationAgent(jid, password, f"station_{i}", station_pos)
        agents[f"station_{i}"] = agent
        await agent.start()
    
    print(f"✅ Created {15} Station Agents")
    
    # Create Vehicle Agents
    for i in range(10):
        vehicle_type = 'bus' if i < 6 else 'tram'
        jid = f"vehicle{i}{xmpp_domain}"
        
        # Create simple route
        route_stations = random.sample(city.stations, k=min(5, len(city.stations)))
        route = Route(f"route_{i}", route_stations)
        
        agent = VehicleAgent(jid, password, f"vehicle_{i}", vehicle_type, route, city)
        agents[f"vehicle_{i}"] = agent
        await agent.start()
    
    print(f"✅ Created {10} Vehicle Agents")
    
    # Create Passenger Agents
    for i in range(20):
        jid = f"passenger{i}{xmpp_domain}"
        origin = random.choice(city.stations)
        destination = random.choice([s for s in city.stations if s != origin])
        
        agent = PassengerAgent(jid, password, f"passenger_{i}", origin, destination)
        agents[f"passenger_{i}"] = agent
        await agent.start()
    
    print(f"✅ Created {20} Passenger Agents")
    
    # Create Maintenance Agents
    for i in range(3):
        jid = f"maintenance{i}{xmpp_domain}"
        base_pos = random.choice(city.stations)
        
        agent = MaintenanceAgent(jid, password, f"maintenance_{i}", base_pos, city)
        agents[f"maintenance_{i}"] = agent
        await agent.start()
    
    print(f"✅ Created {3} Maintenance Agents")
    
    return agents

async def main():
    print("🚌 Starting SPADE Multi-Agent Transportation System")
    print("=" * 60)
    print("⚠️  REQUIREMENTS:")
    print("   - XMPP server must be running on localhost:5222")
    print("   - Install: ejabberd or Prosody")
    print("   - Create users: station0-14, vehicle0-9, passenger0-19, maintenance0-2")
    print("=" * 60)
    
    try:
        # Create city environment
        city = City(SIMULATION_CONFIG['city'])
        print(f"✅ City created: {len(city.stations)} stations, {city.grid_size} grid")
        
        # Create metrics collector
        metrics_collector = MetricsCollector()
        print(f"✅ Metrics collector initialized")
        
        # Create event manager for dynamic events
        event_manager = EventManager(city)
        event_scheduler = EventScheduler(event_manager)
        print(f"✅ Event system initialized")
        
        # Create and start SPADE agents
        agents_registry = await create_spade_agents(city)
        print(f"\n✅ Total agents running: {len(agents_registry)}")
        
        # Inject event_manager into agents
        for agent_id, agent in agents_registry.items():
            if hasattr(agent, 'event_manager'):
                agent.event_manager = event_manager
        print(f"✅ Event system connected to agents")
        
        # Create and start dashboard
        dashboard = SPADEDashboardServer(city, agents_registry, metrics_collector, port=8080)
        await dashboard.start()
        
        # Start event scheduler
        asyncio.create_task(event_scheduler.run_realistic_scenario())
        print(f"✅ Realistic event scenario started")
        
        print("\n" + "=" * 60)
        print("✅ SYSTEM READY!")
        print("🌐 Dashboard: http://localhost:8080")
        print("🤖 SPADE Agents: Active and communicating via XMPP")
        print("🎬 Dynamic Events: Traffic jams, concerts, weather, accidents")
        print("📊 Metrics: Real-time calculation from agents")
        print("=" * 60)
        print("\nPress Ctrl+C to stop\n")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except ConnectionRefusedError:
        print("\n❌ ERROR: Cannot connect to XMPP server!")
        print("   Please start ejabberd or Prosody on localhost:5222")
        print("   For demo without XMPP, run: python demo.py")
    except KeyboardInterrupt:
        print("\n🛑 Stopping system...")
        event_scheduler.stop()
        # Stop all agents
        for agent in agents_registry.values():
            await agent.stop()
        print("✅ All agents stopped")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("   For demo without XMPP, run: python demo.py")

if __name__ == "__main__":
    asyncio.run(main())
