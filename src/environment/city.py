"""
City environment that represents the transportation network
"""
import random
from typing import List, Tuple, Dict
from dataclasses import dataclass

@dataclass(frozen=True)
class Position:
    x: int
    y: int
    
    def distance_to(self, other: 'Position') -> float:
        return ((self.x - other.x)**2 + (self.y - other.y)**2)**0.5
    
    def __eq__(self, other):
        return isinstance(other, Position) and self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((self.x, self.y))

@dataclass
class Route:
    id: str
    stations: List[Position]
    vehicle_type: str  # 'bus' or 'tram'

class City:
    def __init__(self, config: dict):
        self.name = config['name']
        self.grid_size = config['grid_size']
        self.stations = []
        self.station_types = {}  # Position -> 'bus', 'tram', or 'mixed'
        self.routes = []
        self.traffic_conditions = {}  # position -> congestion level (0-1)
        self.weather_active = False  # Rain/weather effects
        
        self._generate_stations(config['num_stations'])
        self._generate_routes()
        self._initialize_traffic()
        self._assign_station_types()
    
    def _generate_stations(self, num_stations: int):
        """Generate station positions across the city grid"""
        for i in range(num_stations):
            # Ensure stations are well distributed
            x = random.randint(1, self.grid_size[0] - 2)
            y = random.randint(1, self.grid_size[1] - 2)
            
            # Avoid placing stations too close to each other
            position = Position(x, y)
            if not any(position.distance_to(existing) < 3 for existing in self.stations):
                self.stations.append(position)
        
        # If we couldn't place enough stations, fill remaining randomly
        while len(self.stations) < num_stations:
            x = random.randint(0, self.grid_size[0] - 1)
            y = random.randint(0, self.grid_size[1] - 1)
            self.stations.append(Position(x, y))
    
    def _generate_routes(self):
        """Generate bus and tram routes connecting stations"""
        # Create main routes (buses)
        for i in range(3):
            route_stations = random.sample(self.stations, min(6, len(self.stations)))
            route_stations.sort(key=lambda p: p.x + p.y)  # Sort for logical order
            self.routes.append(Route(f"bus_route_{i}", route_stations, "bus"))
        
        # Create tram routes (more linear)
        for i in range(2):
            route_stations = random.sample(self.stations, min(4, len(self.stations)))
            route_stations.sort(key=lambda p: p.x)  # Sort by x-coordinate
            self.routes.append(Route(f"tram_route_{i}", route_stations, "tram"))
    
    def _initialize_traffic(self):
        """Initialize traffic conditions across the city"""
        for x in range(self.grid_size[0]):
            for y in range(self.grid_size[1]):
                # Base traffic level with some randomness
                self.traffic_conditions[Position(x, y)] = random.uniform(0.1, 0.3)
    
    def _assign_station_types(self):
        """Assign station types based on routes that serve them"""
        for station in self.stations:
            bus_routes = []
            tram_routes = []
            
            for route in self.routes:
                if station in route.stations:
                    if route.vehicle_type == 'bus':
                        bus_routes.append(route)
                    elif route.vehicle_type == 'tram':
                        tram_routes.append(route)
            
            # Determine station type
            if bus_routes and tram_routes:
                self.station_types[station] = 'mixed'
            elif bus_routes:
                self.station_types[station] = 'bus'
            elif tram_routes:
                self.station_types[station] = 'tram'
            else:
                self.station_types[station] = 'mixed'  # Default
    
    def update_traffic(self, time_of_day: int):
        """Update traffic conditions based on time of day"""
        # Rush hour traffic simulation
        rush_multiplier = 1.0
        if 7 <= time_of_day <= 9 or 17 <= time_of_day <= 19:
            rush_multiplier = 2.5
        
        for position in self.traffic_conditions:
            base_level = random.uniform(0.1, 0.3)
            self.traffic_conditions[position] = min(1.0, base_level * rush_multiplier)
    
    def get_traffic_level(self, position: Position) -> float:
        """Get current traffic congestion level at position"""
        return self.traffic_conditions.get(position, 0.5)
    
    def get_nearest_station(self, position: Position) -> Position:
        """Find the nearest station to a given position"""
        return min(self.stations, key=lambda s: position.distance_to(s))
    
    def get_route_by_stations(self, start: Position, end: Position) -> List[Route]:
        """Find routes that connect two stations"""
        connecting_routes = []
        for route in self.routes:
            if start in route.stations and end in route.stations:
                connecting_routes.append(route)
        return connecting_routes
    
    def activate_weather(self, weather_type: str = 'rain'):
        """Activate weather effects (rain reduces speed, increases breakdowns)"""
        self.weather_active = True
        print(f"🌧️ Weather activated: {weather_type}")
    
    def deactivate_weather(self):
        """Deactivate weather effects"""
        self.weather_active = False
        print(f"☀️ Weather cleared")
    
    def get_station_type(self, position: Position) -> str:
        """Get the type of station at a position"""
        return self.station_types.get(position, 'mixed')