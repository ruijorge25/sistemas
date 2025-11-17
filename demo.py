"""
Demo script with web dashboard - No XMPP required
"""
import asyncio
import time
import random
import math
from aiohttp import web
from src.environment.city import City, Position, Route
from src.config.settings import SIMULATION_CONFIG

class MockAgent:
    """Mock agent for demonstration purposes"""
    def __init__(self, agent_id, position, agent_type):
        self.id = agent_id
        self.position = position
        self.agent_type = agent_type
        self.is_broken = False
        self.passenger_queue = []
        self.capacity = 50 if agent_type == 'bus' else (30 if agent_type == 'tram' else 0)
        self.passengers = []
        self.fuel_level = random.uniform(0.6, 1.0)
        self.target_vehicle = None  # For maintenance agents
        
    def update_position(self, new_position):
        self.position = new_position

class DemoSimulation:
    """Demonstration simulation with web dashboard"""
    
    def __init__(self, port=9000):
        self.city = City(SIMULATION_CONFIG['city'])
        self.vehicles = {}
        self.stations = {}
        self.maintenance_agents = []  # Track maintenance teams
        self.simulation_time = 0
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        """Setup web API routes"""
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/api/vehicles', self.api_vehicles)
        self.app.router.add_get('/api/stations', self.api_stations)
        self.app.router.add_get('/api/metrics', self.api_metrics)
        self.app.router.add_get('/api/status', self.api_status)
        
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
        
        # Add regular vehicles
        for v in self.vehicles.values():
            vehicles_data.append({
                'id': v.id,
                'type': v.vehicle_type,
                'position': [v.position.x, v.position.y],
                'capacity': v.capacity,
                'passengers': len(v.passengers),
                'fuel': v.fuel_level,
                'status': 'broken' if v.is_broken else 'active'
            })
        
        # Add maintenance agents
        for m in self.maintenance_agents:
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
            stations_data.append({
                'name': s.id,
                'position': [s.position.x, s.position.y],
                'waiting_passengers': len(s.passenger_queue),
                'predicted_demand': len(s.passenger_queue) * 1.2
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
            'total_stations': len(self.stations)
        })
        
    def setup_demo_agents(self):
        """Create mock agents for demonstration"""
        # Create mock vehicles
        for i in range(10):
            vehicle_id = f"vehicle_{i}"
            vehicle_type = 'bus' if i < 6 else 'tram'
            start_pos = self.city.stations[i % len(self.city.stations)]
            
            vehicle = MockAgent(vehicle_id, start_pos, vehicle_type)
            vehicle.vehicle_type = vehicle_type
            vehicle.position = start_pos
            vehicle.passengers = [f"p{j}" for j in range(random.randint(5, 25))]
            self.vehicles[vehicle_id] = vehicle
        
        # Create mock stations
        for i, station_pos in enumerate(self.city.stations[:15]):
            station_id = f"station_{i}"
            station = MockAgent(station_id, station_pos, 'station')
            queue_size = random.randint(0, 30)
            station.passenger_queue = [f"passenger_{j}" for j in range(queue_size)]
            self.stations[station_id] = station
        
        # Create mock stations
        for i, station_pos in enumerate(self.city.stations):
            station_id = f"station_{i}"
            station = MockAgent(station_id, station_pos, 'station')
            queue_size = random.randint(0, 30)
            station.passenger_queue = [f"passenger_{j}" for j in range(queue_size)]
            self.stations[station_id] = station
    
    def update_simulation(self):
        """Update simulation state"""
        self.simulation_time += 1
        
        # Maintenance system - dispatch teams to broken vehicles
        broken_vehicles = [v for v in self.vehicles.values() if v.is_broken]
        
        # Create maintenance agents for broken vehicles
        for vehicle in broken_vehicles:
            # Check if already has a maintenance agent assigned
            assigned = any(m.target_vehicle == vehicle.id for m in self.maintenance_agents)
            if not assigned:
                # Create new maintenance agent near the broken vehicle
                maint_id = f"maint_{len(self.maintenance_agents)}"
                maint_agent = MockAgent(maint_id, vehicle.position, 'maintenance')
                maint_agent.target_vehicle = vehicle.id
                self.maintenance_agents.append(maint_agent)
                print(f"🚑 Maintenance team {maint_id} dispatched to repair {vehicle.id}")
        
        # Update maintenance agents - repair vehicles
        for maint in list(self.maintenance_agents):
            if maint.target_vehicle:
                target = self.vehicles.get(maint.target_vehicle)
                if target and target.is_broken:
                    # Move towards broken vehicle
                    if maint.position.x != target.position.x or maint.position.y != target.position.y:
                        dx = 1 if target.position.x > maint.position.x else (-1 if target.position.x < maint.position.x else 0)
                        dy = 1 if target.position.y > maint.position.y else (-1 if target.position.y < maint.position.y else 0)
                        new_x = maint.position.x + dx
                        new_y = maint.position.y + dy
                        maint.position = Position(new_x, new_y)
                    else:
                        # Repair the vehicle (instant when at same position)
                        target.is_broken = False
                        print(f"✅ {maint.id} successfully repaired {target.id}")
                        self.maintenance_agents.remove(maint)
                else:
                    # Target no longer broken, remove maintenance agent
                    self.maintenance_agents.remove(maint)
        
        # Move vehicles randomly
        for vehicle in self.vehicles.values():
            if not vehicle.is_broken and random.random() < 0.3:
                # Move to nearby position
                new_x = max(0, min(19, vehicle.position.x + random.choice([-1, 0, 1])))
                new_y = max(0, min(19, vehicle.position.y + random.choice([-1, 0, 1])))
                vehicle.position = Position(new_x, new_y)
                
            # Random breakdown (very rare - 0.08% chance)
            if not vehicle.is_broken and random.random() < 0.0008:
                vehicle.is_broken = True
                print(f"💥 {vehicle.id} broke down at ({vehicle.position.x}, {vehicle.position.y})")
                
            # Update passengers
            if not vehicle.is_broken:
                if random.random() < 0.2:
                    if len(vehicle.passengers) < vehicle.capacity:
                        vehicle.passengers.append(f"p{random.randint(1000, 9999)}")
                if random.random() < 0.15 and vehicle.passengers:
                    vehicle.passengers.pop()
                
            # Update fuel
            if not vehicle.is_broken:
                vehicle.fuel_level = max(0.1, min(1.0, vehicle.fuel_level + random.uniform(-0.02, 0.05)))
        
        # Update stations
        for station in self.stations.values():
            # Add/remove passengers randomly
            if random.random() < 0.3:
                station.passenger_queue.append(f"p{random.randint(1000, 9999)}")
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