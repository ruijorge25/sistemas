"""
Demo with Web Dashboard - No XMPP Required
Simple simulation with web interface
"""
import asyncio
from aiohttp import web
import json
from src.environment.city import City
from src.config.settings import SIMULATION_CONFIG
import random

class SimpleDashboardServer:
    def __init__(self, city, port=8080):
        self.city = city
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        self.simulation_time = 0
        self.vehicles = []
        self.metrics = {
            'fleet_utilization': 0.85,
            'average_waiting_time': 5.2,
            'on_time_performance': 0.87,
            'passenger_satisfaction': 0.82,
            'breakdown_response_time': 3.5,
            'route_adaptations': 0,
            'contract_net_activations': 0
        }
        self.init_vehicles()
    
    def init_vehicles(self):
        """Initialize demo vehicles"""
        self.vehicles = [
            {
                'id': f'vehicle_{i}',
                'type': 'bus' if i < 3 else 'tram',
                'position': [self.city.stations[i % len(self.city.stations)].x, 
                            self.city.stations[i % len(self.city.stations)].y],
                'capacity': 50,
                'passengers': random.randint(10, 45),
                'fuel': random.uniform(0.5, 1.0),
                'status': 'active'
            }
            for i in range(5)
        ]
    
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
        """API: Vehicle data"""
        return web.json_response(self.vehicles)
    
    async def api_stations(self, request):
        """API: Station data"""
        stations = [
            {
                'name': f'Station {i+1}',
                'position': [s.x, s.y],
                'waiting_passengers': random.randint(0, 30)
            }
            for i, s in enumerate(self.city.stations)
        ]
        return web.json_response(stations)
    
    async def api_metrics(self, request):
        """API: Performance metrics"""
        # Simulate changing metrics
        self.metrics['fleet_utilization'] = min(1.0, self.metrics['fleet_utilization'] + random.uniform(-0.05, 0.05))
        self.metrics['average_waiting_time'] = max(1.0, self.metrics['average_waiting_time'] + random.uniform(-0.5, 0.5))
        return web.json_response(self.metrics)
    
    async def update_simulation(self):
        """Update simulation state"""
        while True:
            await asyncio.sleep(2)
            self.simulation_time += 2
            
            # Move vehicles randomly
            for vehicle in self.vehicles:
                if random.random() < 0.3:
                    vehicle['position'] = [
                        max(0, min(19, vehicle['position'][0] + random.randint(-1, 1))),
                        max(0, min(19, vehicle['position'][1] + random.randint(-1, 1)))
                    ]
                    vehicle['passengers'] = min(vehicle['capacity'], 
                                               max(0, vehicle['passengers'] + random.randint(-5, 10)))
    
    async def start(self):
        """Start the dashboard server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        print(f"🌐 Dashboard running at http://localhost:{self.port}")
        
        # Start simulation update loop
        asyncio.create_task(self.update_simulation())

async def main():
    print("🚌 Starting Transportation System with Dashboard")
    print("=" * 50)
    
    # Create city
    city = City(SIMULATION_CONFIG['city'])
    print(f"✅ City created with {len(city.stations)} stations")
    
    # Create and start dashboard
    dashboard = SimpleDashboardServer(city, port=8080)
    await dashboard.start()
    
    print("\n✅ System ready!")
    print("📊 Open your browser: http://localhost:8080")
    print("\nPress Ctrl+C to stop")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")

if __name__ == "__main__":
    asyncio.run(main())
