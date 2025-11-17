"""
Demo script with web dashboard - No XMPP required
"""
import asyncio
import time
import random
import math
from aiohttp import web
from src.environment.city import City, Position, Route
from src.environment.base_manager import BaseManager
from src.environment.traffic_manager import TrafficManager
from src.config.settings import SIMULATION_CONFIG, BREAKDOWN_TYPES

class MockAgent:
    """Mock agent for demonstration purposes"""
    def __init__(self, agent_id, position, agent_type):
        self.id = agent_id
        self.position = position
        self.agent_type = agent_type
        self.is_broken = False
        self.breakdown_type = None  # 'tire', 'engine', or 'tow'
        self.passenger_queue = []
        # Use correct capacity based on type
        if agent_type == 'bus':
            self.capacity = SIMULATION_CONFIG['vehicle']['bus_capacity']  # 60
        elif agent_type == 'tram':
            self.capacity = SIMULATION_CONFIG['vehicle']['tram_capacity']  # 40
        else:
            self.capacity = 0
        self.passengers = []
        self.fuel_level = SIMULATION_CONFIG['vehicle']['fuel_capacity']
        self.target_vehicle = None  # For maintenance agents
        self.previous_position = position  # Track movement
        self.direction = (0, 0)  # Track direction: (dx, dy)
        self.state = 'active'  # 'active' or 'at_base'
        self.vehicle_type = agent_type  # Add vehicle_type attribute
        
    def update_position(self, new_position):
        self.position = new_position

class DemoSimulation:
    """Demonstration simulation with web dashboard"""
    
    def __init__(self, port=9000):
        self.city = City(SIMULATION_CONFIG['city'])
        self.base_manager = BaseManager()
        self.traffic_manager = TrafficManager()
        self.vehicles = {}
        self.stations = {}
        self.maintenance_agents = []  # Track maintenance teams
        self.simulation_time = 0
        self.port = port
        self.app = web.Application()
        self.weather_active = False
        self.rush_hour_active = False
        self.setup_routes()
        
    def setup_routes(self):
        """Setup web API routes"""
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/api/vehicles', self.api_vehicles)
        self.app.router.add_get('/api/stations', self.api_stations)
        self.app.router.add_get('/api/metrics', self.api_metrics)
        self.app.router.add_get('/api/status', self.api_status)
        self.app.router.add_get('/api/routes', self.api_routes)
        self.app.router.add_get('/api/bases', self.api_bases)
        
        # Manual control endpoints
        self.app.router.add_post('/api/trigger/rush_hour', self.trigger_rush_hour)
        self.app.router.add_post('/api/trigger/breakdown', self.trigger_breakdown)
        self.app.router.add_post('/api/trigger/weather', self.trigger_weather)
        
    async def index(self, request):
        """Serve dashboard HTML"""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), 
            'src', 'visualization', 'templates', 'dashboard_advanced.html'
        )
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                html = f.read()
            return web.Response(text=html, content_type='text/html')
        except FileNotFoundError:
            return web.Response(text="<h1>Dashboard not found</h1>", content_type='text/html')
    
    async def api_vehicles(self, request):
        """API endpoint for vehicles and maintenance agents"""
        vehicles_data = []
        
        # Add regular vehicles (only if not at base)
        for v in self.vehicles.values():
            if v.state == 'at_base':
                continue  # Skip vehicles at base (not on grid)
                
            vehicles_data.append({
                'id': v.id,
                'type': v.vehicle_type,
                'position': [v.position.x, v.position.y],
                'capacity': v.capacity,
                'passengers': len(v.passengers),
                'fuel': v.fuel_level,
                'status': 'broken' if v.is_broken else 'active',
                'breakdown_type': v.breakdown_type,
                'direction': v.direction
            })
        
        # Add maintenance agents (only if not at base)
        for m in self.maintenance_agents:
            if m.state == 'at_base':
                continue
                
            vehicles_data.append({
                'id': m.id,
                'type': 'maintenance',
                'position': [m.position.x, m.position.y],
                'capacity': 0,
                'passengers': 0,
                'fuel': 1.0,
                'status': 'active',
                'target': m.target_vehicle
            })
        
        return web.json_response(vehicles_data)
    
    async def api_stations(self, request):
        """API endpoint for stations"""
        stations_data = []
        for s in self.stations.values():
            station_type = self.city.get_station_type(s.position)
            stations_data.append({
                'name': s.id,
                'position': [s.position.x, s.position.y],
                'waiting_passengers': len(s.passenger_queue),
                'predicted_demand': len(s.passenger_queue) * 1.2,
                'station_type': station_type  # 'bus', 'tram', or 'mixed'
            })
        return web.json_response(stations_data)
    
    async def api_metrics(self, request):
        """API endpoint for metrics"""
        active_vehicles = sum(1 for v in self.vehicles.values() if not v.is_broken)
        total_passengers = sum(len(v.passengers) for v in self.vehicles.values())
        total_waiting = sum(len(s.passenger_queue) for s in self.stations.values())
        
        return web.json_response({
            'vehicle_utilization': (total_passengers / (len(self.vehicles) * 40)) * 100 if self.vehicles else 0,
            'average_wait_time': total_waiting / len(self.stations) if self.stations else 0,
            'system_efficiency': (active_vehicles / len(self.vehicles)) * 100 if self.vehicles else 0,
            'fuel_efficiency': sum(v.fuel_level for v in self.vehicles.values()) / len(self.vehicles) * 100 if self.vehicles else 0,
            'active_vehicles': active_vehicles,
            'total_vehicles': len(self.vehicles),
            'broken_vehicles': len(self.vehicles) - active_vehicles,
            'total_passengers_transported': total_passengers,
            'total_passengers_waiting': total_waiting,
            'cooperation_rate': random.uniform(15, 35),
            'ml_states_explored': random.randint(100, 300),
            'ml_q_updates': random.randint(500, 1500),
            'active_convoys': random.randint(0, 3),
            'contract_net_activations': random.randint(20, 80),
            'events_active': 0
        })
    
    async def api_status(self, request):
        """API endpoint for status"""
        return web.json_response({
            'status': 'running',
            'simulation_time': self.simulation_time,
            'total_vehicles': len(self.vehicles),
            'total_stations': len(self.stations),
            'weather_active': self.weather_active,
            'rush_hour_active': self.rush_hour_active
        })
    
    async def api_routes(self, request):
        """API endpoint for routes"""
        routes_data = []
        for route in self.city.routes:
            routes_data.append({
                'id': route.id,
                'type': route.vehicle_type,
                'stations': [[s.x, s.y] for s in route.stations]
            })
        return web.json_response(routes_data)
    
    async def api_bases(self, request):
        """API endpoint for base status"""
        return web.json_response(self.base_manager.get_base_status())
    
    # Manual control endpoints
    async def trigger_rush_hour(self, request):
        """Trigger rush hour manually"""
        self.rush_hour_active = True
        for station in self.stations.values():
            # Add extra passengers
            for _ in range(random.randint(10, 20)):
                station.passenger_queue.append(f"rush_passenger_{random.randint(1000, 9999)}")
        print("🚨 RUSH HOUR TRIGGERED - Extra passengers added to all stations!")
        return web.json_response({'status': 'ok', 'message': 'Rush hour activated'})
    
    async def trigger_breakdown(self, request):
        """Trigger random breakdown manually"""
        # Pick a random active vehicle
        active_vehicles = [v for v in self.vehicles.values() if not v.is_broken and v.state == 'active']
        if active_vehicles:
            vehicle = random.choice(active_vehicles)
            # Random breakdown type
            breakdown_types = ['tire', 'engine', 'tow']
            vehicle.breakdown_type = random.choice(breakdown_types)
            vehicle.is_broken = True
            print(f"💥 MANUAL BREAKDOWN: {vehicle.id} - Type: {vehicle.breakdown_type}")
            return web.json_response({'status': 'ok', 'message': f'{vehicle.id} broke down ({vehicle.breakdown_type})'})
        return web.json_response({'status': 'error', 'message': 'No active vehicles to break'})
    
    async def trigger_weather(self, request):
        """Trigger rain weather manually"""
        self.weather_active = not self.weather_active
        if self.weather_active:
            self.city.activate_weather('rain')
            message = 'Rain activated - 50% speed reduction, 20% more breakdowns'
        else:
            self.city.deactivate_weather()
            message = 'Weather cleared'
        return web.json_response({'status': 'ok', 'message': message})
        
    def setup_demo_agents(self):
        """Create mock agents for demonstration"""
        # Create mock vehicles (6 buses, 4 trams)
        for i in range(10):
            vehicle_id = f"vehicle_{i}"
            vehicle_type = 'bus' if i < 6 else 'tram'
            start_pos = self.city.stations[i % len(self.city.stations)]
            
            vehicle = MockAgent(vehicle_id, start_pos, vehicle_type)
            vehicle.position = start_pos
            vehicle.passengers = [f"p{j}" for j in range(random.randint(5, 25))]
            vehicle.state = 'active'
            self.vehicles[vehicle_id] = vehicle
            
            # Register vehicle in base manager
            self.base_manager.register_agent(vehicle_id, vehicle)
            
            # Register initial position
            self.traffic_manager.register_vehicle_position(
                vehicle_id, start_pos, vehicle_type, (0, 0), False
            )
        
        # Create mock stations
        for i, station_pos in enumerate(self.city.stations):
            station_id = f"station_{i}"
            station = MockAgent(station_id, station_pos, 'station')
            queue_size = random.randint(0, 30)
            station.passenger_queue = [f"passenger_{j}" for j in range(queue_size)]
            self.stations[station_id] = station
        
        # Create 3 maintenance vehicles and park them at base
        for i in range(3):
            maint_id = f"maint_{i}"
            base_entry = self.base_manager.get_entry_point('maintenance')
            maint_agent = MockAgent(maint_id, base_entry, 'maintenance')
            maint_agent.state = 'at_base'
            maint_agent.towing_vehicle = False  # Track if currently towing
            self.maintenance_agents.append(maint_agent)
            
            # Register and park maintenance agent
            self.base_manager.register_agent(maint_id, maint_agent)
            self.base_manager.park_at_base(maint_id, 'maintenance')
        
        print(f"✅ Setup complete: {len(self.vehicles)} vehicles, {len(self.stations)} stations, {len(self.maintenance_agents)} maintenance crews at base")
    
    def update_simulation(self):
        """Update simulation state with new features"""
        self.simulation_time += 1
        
        # Calculate speed modifier based on weather
        speed_modifier = 1.0
        breakdown_modifier = 1.0
        if self.weather_active:
            speed_modifier = 1.0 - SIMULATION_CONFIG['weather']['rain_speed_reduction']  # 0.5 (50% slower)
            breakdown_modifier = 1.0 + SIMULATION_CONFIG['weather']['rain_breakdown_increase']  # 1.2 (20% more)
        
        # === MAINTENANCE SYSTEM WITH DETAILED BREAKDOWNS ===
        broken_vehicles = [v for v in self.vehicles.values() if v.is_broken and v.state == 'active']
        
        for vehicle in broken_vehicles:
            # Check if already has a maintenance agent assigned
            assigned = any(m.target_vehicle == vehicle.id for m in self.maintenance_agents)
            if not assigned:
                # Determine resources needed based on breakdown type
                if not vehicle.breakdown_type:
                    vehicle.breakdown_type = random.choice(['tire', 'engine', 'tow'])
                
                tools_needed = 0
                tow_hooks_needed = 0
                
                if vehicle.breakdown_type == 'tire':
                    tools_needed = SIMULATION_CONFIG['maintenance']['tools_for_tire']  # 2
                elif vehicle.breakdown_type == 'engine':
                    tools_needed = SIMULATION_CONFIG['maintenance']['tools_for_engine']  # 5
                elif vehicle.breakdown_type == 'tow':
                    tow_hooks_needed = SIMULATION_CONFIG['maintenance']['tow_hooks_for_tow']  # 1
                
                # Check if we have available maintenance vehicles at base
                available_maint = self.base_manager.get_agents_at_base('maintenance')
                
                if available_maint and self.base_manager.request_resources(tools_needed, tow_hooks_needed):
                    # Deploy a maintenance vehicle from base
                    maint_id = list(available_maint)[0]
                    spawn_pos = self.base_manager.deploy_from_base(maint_id, 'maintenance')
                    
                    if spawn_pos:
                        # Find or create maintenance agent
                        maint_agent = None
                        for m in self.maintenance_agents:
                            if m.id == maint_id:
                                maint_agent = m
                                break
                        
                        if not maint_agent:
                            maint_agent = MockAgent(maint_id, spawn_pos, 'maintenance')
                            self.maintenance_agents.append(maint_agent)
                        
                        maint_agent.position = spawn_pos
                        maint_agent.state = 'active'
                        maint_agent.target_vehicle = vehicle.id
                        maint_agent.tools = tools_needed
                        maint_agent.tow_hooks = tow_hooks_needed
                        maint_agent.towing_vehicle = False
                        
                        print(f"🚑 {maint_id} deployed from base to repair {vehicle.id} ({vehicle.breakdown_type})")
                        print(f"   Resources: {tools_needed} tools, {tow_hooks_needed} tow hooks")
                else:
                    if not available_maint:
                        print(f"⚠️ No maintenance vehicles available at base for {vehicle.id}")
                    else:
                        print(f"⚠️ Insufficient resources for {vehicle.id} ({vehicle.breakdown_type})")
        
        # Update maintenance agents - move and repair
        for maint in list(self.maintenance_agents):
            if maint.state == 'at_base':
                continue
            
            # Check if maintenance is returning to base (no target)
            if not maint.target_vehicle:
                base_entry = self.base_manager.get_entry_point('maintenance')
                
                # Move towards base
                if maint.position.x != base_entry.x or maint.position.y != base_entry.y:
                    dx = 1 if base_entry.x > maint.position.x else (-1 if base_entry.x < maint.position.x else 0)
                    dy = 1 if base_entry.y > maint.position.y else (-1 if base_entry.y < maint.position.y else 0)
                    maint.position = Position(maint.position.x + dx, maint.position.y + dy)
                    maint.direction = (dx, dy)
                else:
                    # Reached base, park
                    self.base_manager.park_at_base(maint.id, 'maintenance')
                    maint.state = 'at_base'
                    print(f"🏠 {maint.id} returned to base")
                continue
                
            # Has target vehicle
            target = self.vehicles.get(maint.target_vehicle)
            if not target or not target.is_broken:
                # Target no longer exists or is fixed, return to base
                maint.target_vehicle = None
                continue
            
            # Get breakdown type for this repair
            breakdown_type = getattr(target, 'breakdown_type', 'tire')
            
            # TOW: If tow type, bring vehicle to base
            if breakdown_type == 'tow' and hasattr(maint, 'towing_vehicle'):
                if maint.towing_vehicle:
                    # Moving to base with vehicle
                    base_entry = self.base_manager.get_entry_point('maintenance')
                    
                    if maint.position.x != base_entry.x or maint.position.y != base_entry.y:
                        # Move both maintenance and towed vehicle towards base
                        dx = 1 if base_entry.x > maint.position.x else (-1 if base_entry.x < maint.position.x else 0)
                        dy = 1 if base_entry.y > maint.position.y else (-1 if base_entry.y < maint.position.y else 0)
                        maint.position = Position(maint.position.x + dx, maint.position.y + dy)
                        target.position = Position(maint.position.x, maint.position.y)  # Towed vehicle follows
                        maint.direction = (dx, dy)
                    else:
                        # Reached base, repair and release
                        target.is_broken = False
                        target.breakdown_type = None
                        self.traffic_manager.repair_vehicle(target.id, target.position)
                        
                        # Release resources and vehicle
                        tools = getattr(maint, 'tools', 0)
                        tow_hooks = getattr(maint, 'tow_hooks', 0)
                        self.base_manager.release_resources(tools, tow_hooks)
                        
                        maint.target_vehicle = None
                        maint.towing_vehicle = False
                        print(f"✅ {maint.id} towed and repaired {target.id} at base")
                else:
                    # Moving to vehicle to start tow
                    if maint.position.x != target.position.x or maint.position.y != target.position.y:
                        dx = 1 if target.position.x > maint.position.x else (-1 if target.position.x < maint.position.x else 0)
                        dy = 1 if target.position.y > maint.position.y else (-1 if target.position.y < maint.position.y else 0)
                        maint.position = Position(maint.position.x + dx, maint.position.y + dy)
                        maint.direction = (dx, dy)
                    else:
                        # Reached vehicle, start towing
                        maint.towing_vehicle = True
                        self.traffic_manager.repair_vehicle(target.id, target.position)  # Unblock rail
                        print(f"🚛 {maint.id} started towing {target.id}")
            else:
                # NORMAL REPAIR (tire/engine): Move to vehicle and repair on-site
                if maint.position.x != target.position.x or maint.position.y != target.position.y:
                    # Move towards broken vehicle
                    dx = 1 if target.position.x > maint.position.x else (-1 if target.position.x < maint.position.x else 0)
                    dy = 1 if target.position.y > maint.position.y else (-1 if target.position.y < maint.position.y else 0)
                    maint.position = Position(maint.position.x + dx, maint.position.y + dy)
                    maint.direction = (dx, dy)
                else:
                    # Reached vehicle, repair it
                    target.is_broken = False
                    target.breakdown_type = None
                    self.traffic_manager.repair_vehicle(target.id, target.position)
                    
                    print(f"✅ {maint.id} repaired {target.id}")
                    
                    # Release resources
                    tools = getattr(maint, 'tools', 0)
                    tow_hooks = getattr(maint, 'tow_hooks', 0)
                    self.base_manager.release_resources(tools, tow_hooks)
                    
                    # Clear target to trigger return to base
                    maint.target_vehicle = None
        
        # === VEHICLE MOVEMENT WITH FUEL CONSUMPTION ===
        for vehicle in self.vehicles.values():
            if vehicle.state == 'at_base':
                # Refuel at base
                vehicle.fuel_level = SIMULATION_CONFIG['vehicle']['fuel_capacity']
                continue
            
            if not vehicle.is_broken and vehicle.fuel_level > 0:
                # Check if should return to base (low fuel)
                if vehicle.fuel_level < 20:
                    base_type = 'bus' if vehicle.vehicle_type == 'bus' else 'tram'
                    base_entry = self.base_manager.get_entry_point(base_type)
                    
                    # Move towards base
                    if vehicle.position.x == base_entry.x and vehicle.position.y == base_entry.y:
                        # At base entrance, park
                        self.traffic_manager.unregister_vehicle_position(vehicle.id, vehicle.position)
                        if self.base_manager.park_at_base(vehicle.id, base_type):
                            vehicle.state = 'at_base'
                            print(f"⛽ {vehicle.id} returned to base for refueling")
                    else:
                        # Move towards base
                        dx = 1 if base_entry.x > vehicle.position.x else (-1 if base_entry.x < vehicle.position.x else 0)
                        dy = 1 if base_entry.y > vehicle.position.y else (-1 if base_entry.y < vehicle.position.y else 0)
                        
                        # Apply speed modifier
                        if random.random() < speed_modifier:
                            new_x = max(0, min(19, vehicle.position.x + dx))
                            new_y = max(0, min(19, vehicle.position.y + dy))
                            new_pos = Position(new_x, new_y)
                            
                            # Check traffic blocking
                            can_move = self.traffic_manager.can_move_to_position(
                                vehicle.id, new_pos, vehicle.vehicle_type, (dx, dy)
                            )
                            
                            if can_move:
                                self.traffic_manager.unregister_vehicle_position(vehicle.id, vehicle.position)
                                vehicle.position = new_pos
                                vehicle.direction = (dx, dy)
                                self.traffic_manager.register_vehicle_position(
                                    vehicle.id, new_pos, vehicle.vehicle_type, (dx, dy), vehicle.is_broken
                                )
                                
                                # Consume fuel (1 unit per cell)
                                vehicle.fuel_level -= SIMULATION_CONFIG['vehicle']['fuel_consumption_per_cell']
                else:
                    # Normal movement (30% chance)
                    if random.random() < 0.3:
                        dx = random.choice([-1, 0, 1])
                        dy = random.choice([-1, 0, 1])
                        
                        # Apply speed modifier (weather effect)
                        if random.random() < speed_modifier:
                            new_x = max(0, min(19, vehicle.position.x + dx))
                            new_y = max(0, min(19, vehicle.position.y + dy))
                            new_pos = Position(new_x, new_y)
                            
                            # Check traffic blocking
                            can_move = self.traffic_manager.can_move_to_position(
                                vehicle.id, new_pos, vehicle.vehicle_type, (dx, dy)
                            )
                            
                            if can_move:
                                self.traffic_manager.unregister_vehicle_position(vehicle.id, vehicle.position)
                                vehicle.position = new_pos
                                vehicle.direction = (dx, dy)
                                self.traffic_manager.register_vehicle_position(
                                    vehicle.id, new_pos, vehicle.vehicle_type, (dx, dy), vehicle.is_broken
                                )
                                
                                # Consume fuel (1 unit per cell)
                                vehicle.fuel_level -= SIMULATION_CONFIG['vehicle']['fuel_consumption_per_cell']
            
            # Random breakdown with weather modifier
            if not vehicle.is_broken and vehicle.state == 'active':
                breakdown_chance = SIMULATION_CONFIG['vehicle']['breakdown_probability'] * breakdown_modifier
                if random.random() < breakdown_chance:
                    vehicle.is_broken = True
                    vehicle.breakdown_type = random.choice(['tire', 'engine', 'tow'])
                    self.traffic_manager.register_vehicle_position(
                        vehicle.id, vehicle.position, vehicle.vehicle_type, vehicle.direction, True
                    )
                    print(f"💥 {vehicle.id} broke down at ({vehicle.position.x}, {vehicle.position.y}) - Type: {vehicle.breakdown_type}")
            
            # Update passengers with overcrowding penalty
            if not vehicle.is_broken and vehicle.state == 'active':
                # Boarding
                if random.random() < 0.2:
                    if len(vehicle.passengers) < vehicle.capacity:
                        vehicle.passengers.append(f"p{random.randint(1000, 9999)}")
                
                # Alighting
                if random.random() < 0.15 and vehicle.passengers:
                    vehicle.passengers.pop()
        
        # === UPDATE STATIONS ===
        for station in self.stations.values():
            # Add passengers (with rush hour modifier)
            arrival_rate = 0.3
            if self.rush_hour_active:
                arrival_rate *= 3.0
            
            if random.random() < arrival_rate:
                station.passenger_queue.append(f"p{random.randint(1000, 9999)}")
            
            # Remove passengers randomly (simulating boarding)
            if random.random() < 0.2 and station.passenger_queue:
                station.passenger_queue.pop()
    
    async def simulation_loop(self):
        """Main simulation loop"""
        while True:
            self.update_simulation()
            await asyncio.sleep(2)
    
    async def start_server(self):
        """Start the web server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        
        print(f"\n{'='*60}")
        print(f"🌐 Dashboard: http://localhost:{self.port}")
        print(f"{'='*60}\n")
        print(f"📊 System:")
        print(f"   • Vehicles: {len(self.vehicles)}")
        print(f"   • Stations: {len(self.stations)}")
        print(f"\n🚀 Demo running! Press Ctrl+C to stop.\n")
    
    async def run_demo(self):
        """Run the demo with web server"""
        self.setup_demo_agents()
        await self.start_server()
        await self.simulation_loop()

async def main():
    print("\n" + "="*60)
    print("🚌 Transportation System Demo")
    print("   Web Dashboard - No XMPP Required")
    print("="*60 + "\n")
    
    demo = DemoSimulation(port=9000)
    
    try:
        await demo.run_demo()
    except KeyboardInterrupt:
        print("\n🛑 Demo stopped\n")

if __name__ == "__main__":
    asyncio.run(main())