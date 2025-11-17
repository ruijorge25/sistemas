"""
Main entry point - Real SPADE Multi-Agent System with Dashboard
Requires XMPP server running on localhost:5222
"""
import asyncio
from aiohttp import web
import json
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
        self.app.router.add_get('/api/bases', self.api_bases)  # New endpoint
    
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

async def create_spade_agents(city, base_manager, traffic_manager):
    """Create and start real SPADE agents"""
    agents = {}
    
    print("🤖 Creating SPADE agents...")
    
    # NO XMPP MODE - Use local memory instead
    use_xmpp = False  # Set to True if XMPP server is running
    
    if use_xmpp:
        xmpp_server = "localhost"
        xmpp_domain = "@localhost"
        password = "password"
    else:
        # Use dummy JIDs for local mode
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
        agent = StationAgent(jid, password, f"station_{i}", station_pos)
        agents[f"station_{i}"] = agent
        if use_xmpp:
            await agent.start()
    
    print(f"✅ Created {15} Station Agents")
    
    # Create Vehicle Agents
    for i in range(10):
        vehicle_type = 'bus' if i < 6 else 'tram'
        jid = f"vehicle{i}{xmpp_domain}"
        
        # Create simple route with vehicle_type
        route_stations = random.sample(city.stations, k=min(5, len(city.stations)))
        route = Route(id=f"route_{i}", stations=route_stations, vehicle_type=vehicle_type)
        
        agent = VehicleAgent(jid, password, f"vehicle_{i}", vehicle_type, route, city)
        agents[f"vehicle_{i}"] = agent
        if use_xmpp:
            await agent.start()
    
    print(f"✅ Created {10} Vehicle Agents")
    
    # Create Maintenance Agents at base
    for i in range(3):
        jid = f"maintenance{i}{xmpp_domain}"
        agent = MaintenanceAgent(jid, password, f"maint_{i}", city)
        agent.base_position = base_positions['maintenance']
        agent.current_position = base_positions['maintenance']
        agent.base_manager = base_manager
        agent.state = 'at_base'
        
        # Register with base_manager
        base_manager.register_agent(f"maint_{i}", agent)
        base_manager.park_at_base(f"maint_{i}", 'maintenance')
        
        agents[f"maint_{i}"] = agent
        if use_xmpp:
            await agent.start()
        
        print(f"🏠 maint_{i} parked at Maintenance Base")
    
    print(f"✅ Created {3} Maintenance Agents")
    
    return agents

async def simulation_loop(agents_registry, base_manager, traffic_manager):
    """Main simulation loop that updates all agents"""
    import time as time_module
    while True:
        await asyncio.sleep(2)  # Update every 2 seconds
        
        # Update vehicle positions and check for breakdowns
        for agent_id, agent in agents_registry.items():
            if 'vehicle' in agent_id:
                # Simple movement simulation
                if not agent.is_broken and agent.next_station:
                    # Move towards next station (simplified)
                    target = agent.next_station
                    dx = target.x - agent.current_position.x
                    dy = target.y - agent.current_position.y
                    
                    # Create new Position instead of modifying frozen dataclass
                    if abs(dx) > abs(dy) and dx != 0:
                        new_x = agent.current_position.x + (1 if dx > 0 else -1)
                        agent.current_position = Position(new_x, agent.current_position.y)
                    elif dy != 0:
                        new_y = agent.current_position.y + (1 if dy > 0 else -1)
                        agent.current_position = Position(agent.current_position.x, new_y)
                    
                    # Check if reached station
                    if agent.current_position.x == target.x and agent.current_position.y == target.y:
                        # Move to next station in route
                        agent.current_station_index = (agent.current_station_index + 1) % len(agent.assigned_route.stations)
                        agent.next_station = agent.assigned_route.stations[agent.current_station_index]
                
                # Random breakdown check
                await agent.check_vehicle_health()
                
                # Dispatch maintenance if broken
                if agent.is_broken and not agent.maintenance_requested:
                    await dispatch_maintenance(agent, agents_registry, base_manager, time_module)
                    agent.maintenance_requested = True
        
        # Update maintenance crews
        for agent_id, agent in agents_registry.items():
            if 'maint_' in agent_id:
                await agent.continue_repair()

async def dispatch_maintenance(vehicle, agents_registry, base_manager, time_module):
    """Dispatch maintenance crew to broken vehicle"""
    # Find available maintenance crew
    available_crews = base_manager.get_agents_at_base('maintenance')
    
    if not available_crews:
        print(f"⚠️ No maintenance vehicles available at base for {vehicle.vehicle_id}")
        return
    
    # Get first available crew
    crew_id = list(available_crews)[0]
    maint = agents_registry.get(crew_id)
    
    if not maint:
        return
    
    # Check resources
    breakdown_type = vehicle.breakdown_type
    resources_needed = BREAKDOWN_TYPES.get(breakdown_type, {'tools': 2, 'tow_hooks': 0})
    
    if not base_manager.allocate_resources(resources_needed['tools'], resources_needed['tow_hooks']):
        print(f"❌ Insufficient resources! Need {resources_needed['tools']} tools and {resources_needed['tow_hooks']} tow hooks")
        print(f"   Available: {base_manager.available_tools} tools, {base_manager.available_tow_hooks} tow hooks")
        print(f"⚠️ Insufficient resources for {vehicle.vehicle_id} ({breakdown_type})")
        return
    
    # Deploy maintenance crew
    base_manager.deploy_agent(crew_id, 'maintenance')
    
    # Create repair job
    from datetime import datetime
    maint.job_queue.append({
        'job_id': f"repair_{vehicle.vehicle_id}",
        'vehicle_id': vehicle.vehicle_id,
        'vehicle_type': vehicle.vehicle_type,
        'position': Position(vehicle.current_position.x, vehicle.current_position.y),
        'breakdown_time': datetime.now(),
        'breakdown_type': breakdown_type,
        'estimated_repair_time': 15,  # seconds
        'priority': 1.0
    })
    
    # Store allocated resources
    maint.allocated_resources = resources_needed
    maint.target_vehicle_agent = vehicle
    
    print(f"🔧 Resources allocated: {resources_needed['tools']} tools, {resources_needed['tow_hooks']} tow hooks")
    print(f"   Remaining: {base_manager.available_tools} tools, {base_manager.available_tow_hooks} tow hooks")
    print(f"🚀 {crew_id} deployed from Maintenance Base at Position({maint.base_position.x}, {maint.base_position.y})")
    print(f"🚑 {crew_id} deployed from base to repair {vehicle.vehicle_id} ({breakdown_type})")
    print(f"   Resources: {resources_needed['tools']} tools, {resources_needed['tow_hooks']} tow hooks")
    
    # Start repair process
    await maint.start_next_repair()

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
