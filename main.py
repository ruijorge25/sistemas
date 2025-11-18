"""
Main entry point - Real SPADE Multi-Agent System with Dashboard
Requires XMPP server running on localhost:5222
"""
import asyncio
from aiohttp import web
import json
import sys
import io

# Fix UTF-8 encoding for Windows console to display emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from src.environment.city import City, Route, Position
from src.environment.base_manager import BaseManager
from src.environment.traffic_manager import TrafficManager
from src.config.settings import SIMULATION_CONFIG, BREAKDOWN_TYPES
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
    def __init__(self, city, agents_registry, metrics_collector, base_manager, traffic_manager, port=8080):
        self.city = city
        self.agents_registry = agents_registry  # Dict of all SPADE agents
        self.metrics_collector = metrics_collector
        self.base_manager = base_manager
        self.traffic_manager = traffic_manager
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
                    'status': 'broken' if agent.is_broken else 'active',
                    'breakdown_type': agent.breakdown_type if agent.is_broken else None
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
    
    async def api_bases(self, request):
        """API: Base information with parked vehicles"""
        bases = {
            'bus': {
                'position': [0, 10],
                'type': 'bus',
                'name': 'Bus Base Norte',
                'parked_vehicles': []
            },
            'tram': {
                'position': [19, 10],
                'type': 'tram',
                'name': 'Tram Base Sul',
                'parked_vehicles': []
            },
            'maintenance': {
                'position': [10, 0],
                'type': 'maintenance',
                'name': 'Maintenance Base Oeste',
                'parked_vehicles': []
            }
        }
        
        # Get parked vehicles from base_manager
        for base_type in ['bus', 'tram', 'maintenance']:
            parked_ids = self.base_manager.get_agents_at_base(base_type)
            for agent_id in parked_ids:
                if agent_id in self.agents_registry:
                    agent = self.agents_registry[agent_id]
                    vehicle_data = {
                        'id': getattr(agent, 'vehicle_id', agent_id),
                        'fuel': getattr(agent, 'fuel_level', 100),
                        'status': 'parked'
                    }
                    bases[base_type]['parked_vehicles'].append(vehicle_data)
        
        return web.json_response(list(bases.values()))
    
    def setup_routes(self):
        """Setup web routes"""
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/api/status', self.api_status)
        self.app.router.add_get('/api/vehicles', self.api_vehicles)
        self.app.router.add_get('/api/stations', self.api_stations)
        self.app.router.add_get('/api/metrics', self.api_metrics)
        self.app.router.add_get('/api/bases', self.api_bases)
        self.app.router.add_get('/api/city', self.api_city)  # New endpoint for city structure
    
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
        vehicle_count = len([a for a in self.agents_registry.keys() if 'vehicle' in a])
        return web.json_response({
            'status': 'running',
            'simulation_time': self.simulation_time,
            'total_vehicles': vehicle_count,
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
    
    async def api_city(self, request):
        """API: City structure for visualization"""
        return web.json_response({
            'grid_size': self.city.grid_size,
            'stations': [[s.x, s.y] for s in self.city.stations],
            'routes': [
                {
                    'id': r.route_id,
                    'vehicle_type': r.vehicle_type,
                    'stations': [[s.x, s.y] for s in r.stations]
                }
                for r in self.city.routes
            ]
        })
    
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

async def create_spade_agents(city, base_manager, traffic_manager):
    """Create and initialize SPADE agents with manual behavior execution"""
    agents = {}
    
    print("🤖 Creating SPADE agents with autonomous behaviors...")
    
    # Local mode - no XMPP connection
    xmpp_domain = "@local"
    password = "local"
    
    # Define base positions
    base_positions = {
        'bus': Position(0, 10),
        'tram': Position(19, 10),
        'maintenance': Position(10, 0)
    }
    
    # Create Station Agents
    for i, station_pos in enumerate(city.stations[:15]):
        jid = f"station{i}{xmpp_domain}"
        agent = StationAgent(jid, password, f"station_{i}", station_pos, city=city)
        # Manually call setup to initialize behaviors WITHOUT starting XMPP connection
        await agent.setup()
        agents[f"station_{i}"] = agent
    
    print(f"✅ Created {15} Station Agents with behaviors")
    
    # Create Vehicle Agents
    for i in range(10):
        vehicle_type = 'bus' if i < 6 else 'tram'
        jid = f"vehicle{i}{xmpp_domain}"
        
        # Create route
        route_stations = random.sample(city.stations, k=min(5, len(city.stations)))
        route = Route(id=f"route_{i}", stations=route_stations, vehicle_type=vehicle_type)
        
        agent = VehicleAgent(jid, password, f"vehicle_{i}", vehicle_type, route, city)
        # Manually call setup to initialize behaviors
        await agent.setup()
        agents[f"vehicle_{i}"] = agent
    
    print(f"✅ Created {10} Vehicle Agents with behaviors")
    
    # Create Passenger Agents (20 passengers with random origins/destinations)
    num_passengers = 20
    for i in range(num_passengers):
        jid = f"passenger{i}{xmpp_domain}"
        
        # Random origin and destination from city stations
        origin_station = random.choice(city.stations)
        destination_station = random.choice([s for s in city.stations if s != origin_station])
        
        agent = PassengerAgent(
            jid, password, f"pass_{i}", 
            origin_station, destination_station, city
        )
        # Manually call setup to initialize behaviors
        await agent.setup()
        agents[f"pass_{i}"] = agent
    
    print(f"✅ Created {num_passengers} Passenger Agents with behaviors")
    
    # Create Maintenance Agents
    for i in range(3):
        jid = f"maintenance{i}{xmpp_domain}"
        agent = MaintenanceAgent(jid, password, f"maint_{i}", city, agents_registry=agents)
        agent.base_position = base_positions['maintenance']
        agent.current_position = base_positions['maintenance']
        agent.base_manager = base_manager
        agent.state = 'at_base'
        
        # Register with base_manager
        base_manager.register_agent(f"maint_{i}", agent)
        base_manager.park_at_base(f"maint_{i}", 'maintenance')
        
        # Manually call setup to initialize behaviors
        await agent.setup()
        agents[f"maint_{i}"] = agent
        
        print(f"🏠 maint_{i} parked at Maintenance Base with behaviors active")
    
    print(f"✅ Created {3} Maintenance Agents with behaviors")
    
    # Provide registry references for agents that need global awareness
    for agent in agents.values():
        if hasattr(agent, 'agents_registry'):
            agent.agents_registry = agents

    # Connect agents - give vehicles reference to maintenance crews
    maintenance_jids = [str(agents[f"maint_{i}"].jid) for i in range(3)]
    for agent_id, agent in agents.items():
        if 'vehicle' in agent_id:
            agent.maintenance_crews_jids = maintenance_jids
            print(f"🔗 {agent_id} connected to {len(maintenance_jids)} maintenance crews")
    
    # Behaviors are added via agent.add_behaviour() but need to be started manually
    # since we're not using SPADE's XMPP connection (local mode)
    print("🎬 Starting agent behavior execution...")
    
    behavior_count = 0
    for agent_id, agent in agents.items():
        for behaviour in agent.behaviours:
            # Start behavior by calling its run() method as a task
            if hasattr(behaviour, 'run'):
                asyncio.create_task(behaviour.run())
                behavior_count += 1
            else:
                print(f"⚠️ Behavior {behaviour.__class__.__name__} in {agent_id} has no run() method!")
    
    print(f"✅ Started {behavior_count} behaviors across {len(agents)} agents!")
    
    return agents

async def simulation_loop(agents_registry, base_manager, traffic_manager):
    """Keep simulation alive - agents work autonomously via their behaviors"""
    simulation_time = 0
    
    print("✅ Simulation running - agents operating autonomously")
    print("📡 Agents communicate via ACL messages")
    print("🤝 Contract Net Protocol active for maintenance negotiations")
    
    while True:
        try:
            await asyncio.sleep(5)  # Just keep alive, agents do their own work
            simulation_time += 5
            
            if simulation_time % 60 == 0:  # Every 60 seconds
                minutes = simulation_time // 60
                print(f"⏱️ Uptime: {minutes}m - {len(agents_registry)} agents active")
        except Exception as e:
            print(f"⚠️ Error in simulation loop: {e}")
            continue

async def main():
    print("🚌 Starting SPADE Multi-Agent Transportation System")
    print("=" * 60)
    print("🎯 Running in LOCAL MODE (no XMPP required)")
    print("=" * 60)
    
    try:
        # Create city environment
        city = City(SIMULATION_CONFIG['city'])
        print(f"✅ City created: {len(city.stations)} stations, {city.grid_size} grid")
        
        # Create base manager and traffic manager
        base_manager = BaseManager()
        traffic_manager = TrafficManager()
        print(f"✅ Base and traffic managers initialized")
        
        # Create metrics collector
        metrics_collector = MetricsCollector()
        print(f"✅ Metrics collector initialized")
        
        # Create event manager for dynamic events
        event_manager = EventManager(city)
        event_scheduler = EventScheduler(event_manager)
        print(f"✅ Event system initialized")
        
        # Create and start SPADE agents
        agents_registry = await create_spade_agents(city, base_manager, traffic_manager)
        print(f"\n✅ Total agents running: {len(agents_registry)}")
        
        # Inject event_manager and traffic_manager into agents
        for agent_id, agent in agents_registry.items():
            if hasattr(agent, 'event_manager'):
                agent.event_manager = event_manager
            # Setup maintenance dispatch system
            if 'vehicle' in agent_id:
                # Give vehicles access to maintenance crews
                agent.maintenance_crews = [agents_registry[f"maint_{i}"] for i in range(3)]
        print(f"✅ Event system connected to agents")
        
        # Create and start dashboard
        dashboard = SPADEDashboardServer(
            city, agents_registry, metrics_collector, 
            base_manager, traffic_manager, port=8080
        )
        await dashboard.start()
        
        # Start simulation loop
        asyncio.create_task(simulation_loop(agents_registry, base_manager, traffic_manager))
        
        # Start event scheduler
        asyncio.create_task(event_scheduler.run_realistic_scenario())
        print(f"✅ Realistic event scenario started")
        
        print("\n" + "=" * 60)
        print("✅ SYSTEM READY!")
        print("🌐 Dashboard: http://localhost:8080")
        print("🤖 SPADE Agents: Active in local mode")
        print("🎬 Dynamic Events: Traffic jams, concerts, weather, accidents")
        print("📊 Metrics: Real-time calculation from agents")
        print("=" * 60)
        print("\nPress Ctrl+C to stop\n")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping system...")
        event_scheduler.stop()
        # Stop all agents
        for agent in agents_registry.values():
            if hasattr(agent, 'stop'):
                await agent.stop()
        print("✅ All agents stopped")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
