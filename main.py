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
from src.config.settings import SIMULATION_CONFIG, BREAKDOWN_TYPES, XMPP_CONFIG
from src.agents.vehicle_agent import VehicleAgent, PassengerInfo
from datetime import datetime, timedelta
from src.agents.station_agent import StationAgent
from src.agents.passenger_agent import PassengerAgent
from src.agents.maintenance_agent import MaintenanceAgent
from src.metrics.collector import MetricsCollector
from src.metrics.analytics import AdvancedAnalytics
from src.environment.events import EventManager, EventScheduler
from src.environment.route_optimizer import FleetRebalancer
import random
import time

class SPADEDashboardServer:
    """Dashboard server that monitors real SPADE agents with advanced analytics"""
    def __init__(self, city, agents_registry, metrics_collector, base_manager, traffic_manager, analytics, event_manager, port=8080):
        self.city = city
        self.agents_registry = agents_registry  # Dict of all SPADE agents
        self.metrics_collector = metrics_collector
        self.analytics = analytics
        self.base_manager = base_manager
        self.traffic_manager = traffic_manager
        self.event_manager = event_manager
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
                # PASSO 6: Use occupancy instead of len(passengers) for accuracy
                passenger_count = agent.occupancy if hasattr(agent, 'occupancy') else len(agent.passengers)
                
                vehicles.append({
                    'id': agent.vehicle_id,
                    'type': agent.vehicle_type,
                    'position': [agent.current_position.x, agent.current_position.y],
                    'capacity': agent.capacity,
                    'passengers': passenger_count,
                    'fuel': agent.fuel_level,
                    'status': 'broken' if agent.is_broken else 'active',
                    'breakdown_type': agent.breakdown_type if agent.is_broken else None
                })
        return vehicles
    
    def get_maintenance_data(self):
        """Get data from maintenance agents"""
        maintenance = []
        for agent_id, agent in self.agents_registry.items():
            if 'maintenance' in agent_id or 'maint' in agent_id:
                # Use current_position directly
                pos = agent.current_position if hasattr(agent, 'current_position') else Position(10, 0)
                
                # Get target vehicle from current job or target_vehicle_agent
                target_vehicle = None
                if hasattr(agent, 'current_job') and agent.current_job:
                    target_vehicle = agent.current_job.get('vehicle_id')
                elif hasattr(agent, 'target_vehicle_agent') and agent.target_vehicle_agent:
                    target_vehicle = getattr(agent.target_vehicle_agent, 'vehicle_id', None)
                
                maintenance.append({
                    'id': agent.crew_id if hasattr(agent, 'crew_id') else agent_id,
                    'position': [pos.x, pos.y],
                    'state': agent.state if hasattr(agent, 'state') else 'idle',
                    'target_vehicle': target_vehicle,
                    'job_queue_size': len(agent.job_queue) if hasattr(agent, 'job_queue') else 0,
                    'is_busy': agent.is_busy if hasattr(agent, 'is_busy') else False
                })
        return maintenance
    
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
        # Get base metrics from MetricsCollector
        metrics = self.metrics_collector.get_current_performance_summary(self.agents_registry)
        
        # PASSO 6: Add fields expected by HTML dashboard
        # Calculate total passengers in vehicles (use occupancy for accuracy)
        total_passengers_in_vehicles = sum(
            (agent.occupancy if hasattr(agent, 'occupancy') else len(agent.passengers))
            for agent_id, agent in self.agents_registry.items()
            if 'vehicle' in agent_id
        )
        
        # Calculate total passengers waiting at stations
        total_passengers_waiting = sum(
            len(agent.passenger_queue) if hasattr(agent, 'passenger_queue') else 0
            for agent_id, agent in self.agents_registry.items()
            if 'station' in agent_id
        )
        
        # Add to metrics response
        metrics['total_passengers_in_vehicles'] = total_passengers_in_vehicles
        metrics['total_passengers_waiting'] = total_passengers_waiting
        metrics['total_vehicles'] = metrics.get('vehicles', 0)
        
        return metrics
    
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
        self.app.router.add_get('/api/maintenance', self.api_maintenance)
        self.app.router.add_get('/api/metrics', self.api_metrics)
        self.app.router.add_get('/api/bases', self.api_bases)
        self.app.router.add_get('/api/city', self.api_city)
        # PHASE 2: Advanced Analytics Endpoints
        self.app.router.add_get('/api/analytics/comprehensive', self.api_analytics_comprehensive)
        self.app.router.add_get('/api/analytics/operational', self.api_analytics_operational)
        self.app.router.add_get('/api/analytics/passenger', self.api_analytics_passenger)
        self.app.router.add_get('/api/analytics/maintenance', self.api_analytics_maintenance)
        self.app.router.add_get('/api/analytics/efficiency', self.api_analytics_efficiency)
        # PASSO 6: Environment control endpoints
        self.app.router.add_post('/api/environment/traffic', self.api_set_traffic)
        self.app.router.add_post('/api/environment/demand', self.api_set_demand)
    
    async def index(self, request):
        """Serve simple dashboard"""
        import os
        template_path = os.path.join(os.path.dirname(__file__), 'src', 'visualization', 'templates', 'dashboard_simple.html')
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
    
    async def api_maintenance(self, request):
        """API: Maintenance crew data"""
        return web.json_response(self.get_maintenance_data())
    
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
                    'id': r.id,
                    'vehicle_type': r.vehicle_type,
                    'stations': [[s.x, s.y] for s in r.stations]
                }
                for r in self.city.routes
            ],
            'traffic_conditions': {
                f"{pos.x},{pos.y}": level 
                for pos, level in self.city.traffic_conditions.items()
            },
            'weather_active': self.city.weather_active
        })
    
    # ============ PHASE 2: ADVANCED ANALYTICS ENDPOINTS ============
    
    async def api_analytics_comprehensive(self, request):
        """API: Comprehensive analytics report"""
        try:
            report = self.analytics.generate_comprehensive_report(self.agents_registry)
            return web.json_response(report)
        except Exception as e:
            return web.json_response({'error': str(e), 'status': 'failed'}, status=500)
    
    async def api_analytics_operational(self, request):
        """API: Operational excellence KPIs"""
        try:
            kpis = self.analytics.calculate_operational_kpis(self.agents_registry)
            return web.json_response(kpis)
        except Exception as e:
            return web.json_response({'error': str(e), 'status': 'failed'}, status=500)
    
    async def api_analytics_passenger(self, request):
        """API: Passenger experience KPIs"""
        try:
            kpis = self.analytics.calculate_passenger_experience_kpis(self.agents_registry)
            return web.json_response(kpis)
        except Exception as e:
            return web.json_response({'error': str(e), 'status': 'failed'}, status=500)
    
    async def api_analytics_maintenance(self, request):
        """API: Maintenance performance KPIs"""
        try:
            kpis = self.analytics.calculate_maintenance_kpis(self.agents_registry)
            return web.json_response(kpis)
        except Exception as e:
            return web.json_response({'error': str(e), 'status': 'failed'}, status=500)
    
    async def api_analytics_efficiency(self, request):
        """API: System efficiency KPIs"""
        try:
            kpis = self.analytics.calculate_efficiency_kpis(self.agents_registry)
            return web.json_response(kpis)
        except Exception as e:
            return web.json_response({'error': str(e), 'status': 'failed'}, status=500)
    
    async def api_set_traffic(self, request):
        """
        PASSO 6: Set global traffic level
        POST /api/environment/traffic
        Body: {"level": float}  # 1.0 = normal, >1.0 = congested
        """
        try:
            data = await request.json()
            level = float(data.get('level', 1.0))
            
            if level < 0.5 or level > 3.0:
                return web.json_response({
                    'status': 'error',
                    'message': 'Traffic level must be between 0.5 and 3.0'
                }, status=400)
            
            self.event_manager.set_global_traffic(level)
            
            return web.json_response({
                'status': 'success',
                'traffic_level': level,
                'message': f'Global traffic set to {level:.1f}x'
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    async def api_set_demand(self, request):
        """
        PASSO 6: Set station demand multiplier
        POST /api/environment/demand
        Body: {
            "station_id": str,
            "factor": float,  # 1.0 = normal, >1.0 = higher demand
            "duration_ticks": int  # How many ticks to last
        }
        """
        try:
            data = await request.json()
            station_id = data.get('station_id')
            factor = float(data.get('factor', 1.0))
            duration = int(data.get('duration_ticks', 100))
            
            if not station_id:
                return web.json_response({
                    'status': 'error',
                    'message': 'station_id is required'
                }, status=400)
            
            if factor < 0.0 or factor > 5.0:
                return web.json_response({
                    'status': 'error',
                    'message': 'Demand factor must be between 0.0 and 5.0'
                }, status=400)
            
            self.event_manager.set_station_demand_multiplier(station_id, factor, duration)
            
            return web.json_response({
                'status': 'success',
                'station_id': station_id,
                'factor': factor,
                'duration_ticks': duration,
                'message': f'Station {station_id} demand set to {factor:.1f}x for {duration} ticks'
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
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

async def create_spade_agents(city, base_manager, traffic_manager, analytics, event_manager, metrics_collector):
    """Create and start SPADE agents in LOCAL MODE"""
    agents = {}
    
    print("🤖 Creating SPADE agents with autonomous behaviors...")
    
    # LOCAL MODE - no XMPP server required
    xmpp_domain = "@local"
    password = "local"
    
    # Define base positions
    base_positions = {
        'bus': Position(0, 10),
        'tram': Position(19, 10),
        'maintenance': Position(10, 0)
    }
    
    # Create Station Agents with REALISTIC INITIAL POPULATION
    for i, station_pos in enumerate(city.stations[:15]):
        jid = f"station{i}{xmpp_domain}"
        # Stations start with 3-8 passengers (realistic)
        initial_passengers = random.randint(3, 8)
        agent = StationAgent(jid, password, f"station_{i}", station_pos, city=city, initial_passengers=initial_passengers, metrics_collector=metrics_collector)
        # LOCAL MODE: only setup (no XMPP server needed)
        await agent.setup()
        agents[f"station_{i}"] = agent
    
    print(f"✅ Created {15} Station Agents with behaviors")
    
    # Create Vehicle Agents with REALISTIC INITIAL PASSENGERS
    vehicle_registry = {}  # Registry for CNP vehicle discovery
    for i in range(10):
        vehicle_type = 'bus' if i < 6 else 'tram'
        jid = f"vehicle{i}{xmpp_domain}"
        
        # Create route - ENSURE at least 3 distinct stations for circular routing
        num_stations = max(3, min(6, len(city.stations)))
        route_stations = random.sample(city.stations[:15], k=num_stations)
        
        # Make route circular by adding first station at the end (enables continuous loop)
        if route_stations[0] not in route_stations[1:]:
            route_stations.append(route_stations[0])
        
        route = Route(id=f"route_{i}", stations=route_stations, vehicle_type=vehicle_type)
        
        # Vehicles start with 5-15 passengers (realistic)
        capacity = 60 if vehicle_type == 'bus' else 40
        initial_passenger_count = random.randint(5, min(15, capacity // 3))
        initial_passengers = [
            PassengerInfo(
                id=f"initial_{vehicle_type}_{i}_{p}",
                origin=route_stations[0],
                destination=random.choice(route_stations[1:]),
                boarding_time=datetime.now(),
                target_arrival_time=datetime.now() + timedelta(minutes=10)
            )
            for p in range(initial_passenger_count)
        ]
        
        agent = VehicleAgent(jid, password, f"vehicle_{i}", vehicle_type, route, city, initial_passengers=initial_passengers, metrics_collector=metrics_collector)
        agent.analytics = analytics  # Inject analytics for event recording
        # LOCAL MODE: only setup (no XMPP server needed)
        await agent.setup()
        agents[f"vehicle_{i}"] = agent
        vehicle_registry[f"vehicle_{i}"] = agent  # Add to registry
    
    print(f"✅ Created {10} Vehicle Agents with behaviors")
    
    # INJECT vehicle_registry into all stations for CNP discovery
    for station_name, station_agent in agents.items():
        if station_name.startswith("station_"):
            station_agent.vehicle_registry = vehicle_registry
    print(f"✅ Injected vehicle_registry into {15} stations for CNP")
    
    # 🆕 CREATE PASSENGER AGENTS (real SPADE agents for negotiation)
    passenger_agents = []
    num_passengers = 10  # Start with 10 active passengers
    
    print(f"🚶 Creating {num_passengers} Passenger Agents...")
    
    for i in range(num_passengers):
        # Generate random origin and destination
        origin_pos = random.choice(city.stations)
        destination_pos = random.choice([s for s in city.stations if s != origin_pos])
        
        jid = f"passenger{i}{xmpp_domain}"
        passenger_id = f"pass_{i}"
        
        # Get nearby vehicle JIDs for negotiation
        nearby_vehicles = [f"vehicle{j}{xmpp_domain}" for j in range(10)]
        
        passenger = PassengerAgent(
            jid=jid,
            password=password,
            passenger_id=passenger_id,
            origin=origin_pos,
            destination=destination_pos,
            city=city,
            nearby_vehicles=nearby_vehicles
        )
        
        # LOCAL MODE: only setup (no XMPP server needed)
        await passenger.setup()
        passenger_agents.append(passenger)
        agents[passenger_id] = passenger
        
        print(f"👤 Passenger {passenger_id}: ({origin_pos.x},{origin_pos.y}) → ({destination_pos.x},{destination_pos.y})")
    
    print(f"✅ Created {num_passengers} Passenger Agents with autonomous negotiation")
    
    # Create Maintenance Agents
    for i in range(3):
        jid = f"maintenance{i}{xmpp_domain}"
        agent = MaintenanceAgent(jid, password, f"maint_{i}", city, event_manager=event_manager, metrics_collector=metrics_collector)
        agent.base_position = base_positions['maintenance']
        agent.current_position = base_positions['maintenance']
        agent.base_manager = base_manager
        agent.state = 'idle'  # PASSO 4: Use lowercase 'idle' not 'at_base'
        
        # Register with base_manager
        base_manager.register_agent(f"maint_{i}", agent)
        base_manager.park_at_base(f"maint_{i}", 'maintenance')
        
        # LOCAL MODE: only setup (no XMPP server needed)
        await agent.setup()
        agents[f"maint_{i}"] = agent
        
        print(f"🏠 maint_{i} parked at Maintenance Base with behaviors active")
    
    print(f"✅ Created {3} Maintenance Agents with behaviors")
    
    # Connect agents - give vehicles reference to maintenance crews
    maintenance_jids = [str(agents[f"maint_{i}"].jid) for i in range(3)]
    for agent_id, agent in agents.items():
        if 'vehicle' in agent_id:
            agent.maintenance_crews_jids = maintenance_jids
            print(f"🔗 {agent_id} connected to {len(maintenance_jids)} maintenance crews")
    
    # Start behaviors manually (LOCAL MODE)
    print("🎬 Starting agent behaviors...")
    
    behavior_count = 0
    for agent_id, agent in agents.items():
        for behaviour in agent.behaviours:
            # Start behavior by calling its run() method as a task
            if hasattr(behaviour, 'run'):
                asyncio.create_task(behaviour.run())
                behavior_count += 1
    
    print(f"✅ Started {behavior_count} behaviors across {len(agents)} agents!")
    
    return agents

async def simulation_loop(agents_registry, base_manager, traffic_manager, analytics, city):
    """Keep simulation alive - agents work autonomously via their behaviors"""
    from src.environment.route_optimizer import RouteOptimizer, FleetRebalancer
    
    simulation_time = 0
    
    # Initialize FleetRebalancer
    route_optimizer = RouteOptimizer(city)
    fleet_rebalancer = FleetRebalancer(city, route_optimizer)
    
    print("✅ Simulation running - agents operating autonomously")
    print("📡 Agents communicate via ACL messages")
    print("🤝 Contract Net Protocol active for maintenance negotiations")
    print("🔄 Fleet rebalancing enabled (checks every 2 minutes)")
    
    while True:
        try:
            await asyncio.sleep(5)  # Just keep alive, agents do their own work
            simulation_time += 5
            
            if simulation_time % 60 == 0:  # Every 60 seconds
                minutes = simulation_time // 60
                print(f"⏱️ Uptime: {minutes}m - {len(agents_registry)} agents active")
            
            # Run fleet rebalancing every 2 minutes
            if simulation_time % 120 == 0:
                vehicles = [a for a in agents_registry.values() if hasattr(a, 'vehicle_id')]
                stations = [a for a in agents_registry.values() if hasattr(a, 'station_id')]
                
                result = await fleet_rebalancer.rebalance_fleet(stations, vehicles)
                
                if result['status'] == 'success' and result['actions_taken'] > 0:
                    print(f"🔄 Fleet rebalanced: {result['actions_taken']} vehicles redirected")
        except Exception as e:
            print(f"⚠️ Error in simulation loop: {e}")
            continue

async def environment_loop(event_manager):
    """
    PASSO 6: Global environment tick loop.
    Calls tick_environment() to decrement event timers.
    """
    tick_rate = SIMULATION_CONFIG['simulation']['time_step']
    tick_count = 0
    
    print(f"🌍 Environment loop starting (tick_rate={tick_rate}s)")
    
    while True:
        try:
            # PASSO 6: Tick environment (decrement timers)
            event_manager.tick_environment()
            
            tick_count += 1
            
            # Log periodically (every 100 ticks = ~10 seconds)
            if tick_count % 100 == 0:
                summary = event_manager.get_active_events_summary()
                if summary['total_active'] > 0:
                    print(f"🌍 Environment tick #{tick_count}: {summary['total_active']} active events")
            
            await asyncio.sleep(tick_rate)
        except Exception as e:
            print(f"⚠️ Error in environment loop: {e}")
            await asyncio.sleep(1)

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
        
        # PHASE 2: Create advanced analytics engine
        analytics = AdvancedAnalytics()
        print(f"✅ Advanced analytics initialized")
        
        # Create event manager for dynamic events
        event_manager = EventManager(city)
        event_scheduler = EventScheduler(event_manager)
        print(f"✅ Event system initialized")
        
        # Create and start SPADE agents
        agents_registry = await create_spade_agents(city, base_manager, traffic_manager, analytics, event_manager, metrics_collector)
        print(f"\n✅ Total agents running: {len(agents_registry)}")
        
        # 🤝 Connect maintenance crews to each other for coordination
        maintenance_agents = [agents_registry[f"maint_{i}"] for i in range(3)]
        for crew in maintenance_agents:
            crew.maintenance_crews = [c for c in maintenance_agents]  # Include self for simplicity
        print(f"🤝 Maintenance crews connected for coordination")
        
        # Inject event_manager and traffic_manager into agents
        for agent_id, agent in agents_registry.items():
            if hasattr(agent, 'event_manager'):
                agent.event_manager = event_manager
            # Setup maintenance dispatch system
            if 'vehicle' in agent_id:
                # Give vehicles access to maintenance crews
                agent.maintenance_crews = maintenance_agents
        print(f"✅ Event system connected to agents")
        
        # Create and start dashboard with integrated WebSocket
        dashboard = SPADEDashboardServer(
            city, agents_registry, metrics_collector, 
            base_manager, traffic_manager, analytics, event_manager, port=8080
        )
        await dashboard.start()
        
        # Start simulation loop
        asyncio.create_task(simulation_loop(agents_registry, base_manager, traffic_manager, analytics, city))
        
        # PASSO 6: Start environment tick loop
        asyncio.create_task(environment_loop(event_manager))
        print(f"✅ Environment tick loop started")
        
        # Start event scheduler
        asyncio.create_task(event_scheduler.run_realistic_scenario())
        print(f"✅ Realistic event scenario started")
        
        print("\n" + "=" * 60)
        print("✅ SYSTEM READY!")
        print("🌐 Dashboard: http://localhost:8080")
        print("🤖 SPADE Agents: 28 agents running")
        print("🎬 Dynamic Events: Traffic, concerts, weather, accidents")
        print("📊 Metrics: Live from agents")
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
