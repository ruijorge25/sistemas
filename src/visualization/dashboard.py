"""
Web dashboard server for real-time visualization
"""
import asyncio
import json
from datetime import datetime
from aiohttp import web
import aiohttp_jinja2
import jinja2
import os

class DashboardServer:
    """Web server for transportation system dashboard"""
    
    def __init__(self, simulation_coordinator, port=8080):
        self.coordinator = simulation_coordinator
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        self.setup_templates()
        
    def setup_templates(self):
        """Setup Jinja2 templates"""
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        aiohttp_jinja2.setup(
            self.app,
            loader=jinja2.FileSystemLoader(template_dir)
        )
    
    def setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/', self.index_handler)
        self.app.router.add_get('/api/status', self.status_handler)
        self.app.router.add_get('/api/vehicles', self.vehicles_handler)
        self.app.router.add_get('/api/stations', self.stations_handler)
        self.app.router.add_get('/api/metrics', self.metrics_handler)
        self.app.router.add_static('/static', 'static')
    
    @aiohttp_jinja2.template('dashboard.html')
    async def index_handler(self, request):
        """Serve main dashboard page"""
        return {
            'title': 'Transportation System Dashboard',
            'grid_size': self.coordinator.city.grid_size
        }
    
    async def status_handler(self, request):
        """Return system status"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'simulation_time': self.coordinator.current_simulation_time,
            'is_running': self.coordinator.is_running,
            'total_vehicles': len(self.coordinator.vehicle_agents),
            'total_stations': len(self.coordinator.station_agents),
            'total_passengers': sum(len(s.passenger_queue) for s in self.coordinator.station_agents.values())
        }
        return web.json_response(data)
    
    async def vehicles_handler(self, request):
        """Return vehicle data"""
        vehicles = []
        
        for vehicle_id, vehicle_agent in self.coordinator.vehicle_agents.items():
            vehicles.append({
                'id': vehicle_id,
                'type': vehicle_agent.vehicle_type,
                'position': {
                    'x': vehicle_agent.current_position.x,
                    'y': vehicle_agent.current_position.y
                },
                'passengers': len(vehicle_agent.passengers),
                'capacity': vehicle_agent.capacity,
                'is_broken': vehicle_agent.is_broken,
                'fuel_level': vehicle_agent.fuel_level,
                'next_station': {
                    'x': vehicle_agent.next_station.x,
                    'y': vehicle_agent.next_station.y
                } if vehicle_agent.next_station else None
            })
        
        return web.json_response({'vehicles': vehicles})
    
    async def stations_handler(self, request):
        """Return station data"""
        stations = []
        
        for station_id, station_agent in self.coordinator.station_agents.items():
            stations.append({
                'id': station_id,
                'position': {
                    'x': station_agent.position.x,
                    'y': station_agent.position.y
                },
                'queue_length': len(station_agent.passenger_queue),
                'current_demand': station_agent.current_demand,
                'predicted_demand': station_agent.predicted_demand
            })
        
        return web.json_response({'stations': stations})
    
    async def metrics_handler(self, request):
        """Return performance metrics"""
        # Calculate metrics
        active_vehicles = sum(1 for v in self.coordinator.vehicle_agents.values() if not v.is_broken)
        total_vehicles = len(self.coordinator.vehicle_agents)
        
        total_waiting = sum(len(s.passenger_queue) for s in self.coordinator.station_agents.values())
        
        # Average waiting time
        total_waiting_time = sum(s.total_waiting_time for s in self.coordinator.station_agents.values())
        total_served = sum(s.total_passengers_served for s in self.coordinator.station_agents.values())
        avg_waiting = total_waiting_time / total_served if total_served > 0 else 0
        
        # On-time performance
        total_on_time = sum(v.on_time_arrivals for v in self.coordinator.vehicle_agents.values())
        total_arrivals = sum(v.total_arrivals for v in self.coordinator.vehicle_agents.values())
        on_time_rate = total_on_time / total_arrivals if total_arrivals > 0 else 0
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'fleet_utilization': active_vehicles / total_vehicles if total_vehicles > 0 else 0,
            'average_waiting_time': avg_waiting,
            'on_time_performance': on_time_rate,
            'passengers_waiting': total_waiting,
            'active_vehicles': active_vehicles,
            'total_vehicles': total_vehicles
        }
        
        return web.json_response(data)
    
    async def start(self):
        """Start the web server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        
        print(f"🌐 Dashboard running at http://localhost:{self.port}")
    
    async def stop(self):
        """Stop the web server"""
        await self.app.shutdown()
        await self.app.cleanup()