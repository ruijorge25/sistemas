"""
Simple console visualization for the transportation system
"""
import os
import time
from typing import Dict, List, Any
from ..environment.city import Position

class ConsoleVisualizer:
    """Simple console-based visualization of the transportation system"""
    
    def __init__(self, city):
        self.city = city
        self.grid_size = city.grid_size
        
    def clear_screen(self):
        """Clear the console screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def render_city(self, vehicles: Dict[str, Any], stations: Dict[str, Any]):
        """Render the current state of the city"""
        self.clear_screen()
        
        # Create grid
        grid = [['.' for _ in range(self.grid_size[0])] for _ in range(self.grid_size[1])]
        
        # Place stations
        for station_id, station_agent in stations.items():
            x, y = int(station_agent.position.x), int(station_agent.position.y)
            if 0 <= x < self.grid_size[0] and 0 <= y < self.grid_size[1]:
                queue_size = len(station_agent.passenger_queue)
                if queue_size > 10:
                    grid[y][x] = 'S'  # Station with high demand
                elif queue_size > 5:
                    grid[y][x] = 's'  # Station with medium demand
                else:
                    grid[y][x] = '·'  # Station with low demand
        
        # Place vehicles
        for vehicle_id, vehicle_agent in vehicles.items():
            x, y = int(vehicle_agent.current_position.x), int(vehicle_agent.current_position.y)
            if 0 <= x < self.grid_size[0] and 0 <= y < self.grid_size[1]:
                if vehicle_agent.is_broken:
                    grid[y][x] = 'X'  # Broken vehicle
                elif vehicle_agent.vehicle_type == 'bus':
                    grid[y][x] = 'B'  # Bus
                else:
                    grid[y][x] = 'T'  # Tram
        
        # Print header
        print("🚌 Multi-Agent Transportation System - Live View")
        print("=" * 50)
        print("Legend: B=Bus, T=Tram, X=Broken, S=High demand station, s=Medium demand, ·=Low demand")
        print()
        
        # Print grid
        for row in grid:
            print(' '.join(row))
        
        print()
        
        # Print status summary
        active_vehicles = sum(1 for v in vehicles.values() if not v.is_broken)
        total_passengers = sum(len(s.passenger_queue) for s in stations.values())
        
        print(f"Active Vehicles: {active_vehicles}/{len(vehicles)}")
        print(f"Total Passengers Waiting: {total_passengers}")
        print(f"Stations: {len(stations)}")
        
        print("\nPress Ctrl+C to stop simulation")
    
    def show_metrics(self, metrics: Dict[str, float]):
        """Display performance metrics"""
        print("\n📊 Performance Metrics:")
        print("-" * 30)
        for metric_name, value in metrics.items():
            if isinstance(value, float):
                print(f"{metric_name}: {value:.2f}")
            else:
                print(f"{metric_name}: {value}")

def create_web_dashboard():
    """Create a simple web dashboard (placeholder)"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Transportation System Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .grid { display: grid; grid-template-columns: repeat(20, 20px); gap: 1px; }
            .cell { width: 20px; height: 20px; border: 1px solid #ccc; }
            .station { background-color: #4CAF50; }
            .bus { background-color: #2196F3; }
            .tram { background-color: #FF9800; }
            .broken { background-color: #F44336; }
        </style>
    </head>
    <body>
        <h1>🚌 Transportation System Dashboard</h1>
        <div id="dashboard">
            <p>Real-time visualization will be implemented here</p>
            <p>Features to include:</p>
            <ul>
                <li>Interactive city map</li>
                <li>Real-time vehicle tracking</li>
                <li>Passenger queue visualization</li>
                <li>Performance metrics charts</li>
                <li>Agent communication logs</li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    with open('dashboard.html', 'w') as f:
        f.write(html_content)
    
    print("📊 Web dashboard template created: dashboard.html")