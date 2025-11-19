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
    
    def __init__(self, *args, **kwargs):
        """Dual-mode constructor for backward compatibility
        
        Supports:
        - Route(id, stations, vehicle_type) - full specification
        - Route(stations) - minimal (for tests/validator)
        """
        # Case 1: Route(id, stations, vehicle_type)
        if len(args) == 3 and isinstance(args[1], list):
            self.id = args[0]
            self.stations = args[1]
            self.vehicle_type = args[2]
        # Case 2: Route(stations) - for tests
        elif len(args) == 1 and isinstance(args[0], list):
            self.id = "route_anon"
            self.stations = args[0]
            self.vehicle_type = kwargs.get("vehicle_type", "bus")
        # Case 3: Route(id=..., stations=..., vehicle_type=...) - kwargs
        else:
            self.id = kwargs.get("id", "route_anon")
            self.stations = kwargs.get("stations", [])
            self.vehicle_type = kwargs.get("vehicle_type", "bus")

class City:
    def __init__(self, config: dict = None):
        """Initialize city with optional config (defaults for backward compatibility)"""
        if config is None:
            # Default configuration for tests/validator
            config = {
                'name': 'Test City',
                'grid_size': (100, 100),
                'num_stations': 15
            }
        
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
    
    def add_station(self, position: Position, station_type: str = 'mixed'):
        """Add a station to the city (for tests/validators)"""
        if position not in self.stations:
            self.stations.append(position)
            self.station_types[position] = station_type
    
    def get_weather_impact(self) -> float:
        """Get current weather impact multiplier on speed/breakdowns"""
        if self.weather_active:
            return 0.7  # 30% slower in bad weather
        return 1.0
    
    def get_vehicles_within_radius(self, position: Position, radius: float, vehicle_registry: dict) -> List[str]:
        """
        Find all vehicles within a given radius of a position.
        
        Args:
            position: Center position to search from
            radius: Search radius in grid units
            vehicle_registry: Dict mapping vehicle_id -> vehicle_agent reference
        
        Returns:
            List of vehicle JIDs (strings) within the radius
        """
        vehicles_in_range = []
        
        for vehicle_id, vehicle_agent in vehicle_registry.items():
            # Calculate distance from position to vehicle's current position
            distance = position.distance_to(vehicle_agent.current_position)
            
            # Include vehicles within radius that are not broken
            if distance <= radius and not vehicle_agent.is_broken:
                vehicles_in_range.append(str(vehicle_agent.jid))
        
        return vehicles_in_range
    
    def get_station_jid(self, station_id: str) -> str:
        """
        Map station_id to JID for messaging.
        
        Args:
            station_id: Station identifier (e.g., 'station_3')
            
        Returns:
            JID string (e.g., 'station3@local')
        """
        # Extract number from station_id (handles 'station_3' or 'station3')
        import re
        match = re.search(r'\d+', station_id)
        if match:
            num = match.group()
            return f"station{num}@local"
        return f"{station_id}@local"
    
    def get_vehicle_jid(self, vehicle_id: str) -> str:
        """
        Map vehicle_id to JID for messaging.
        
        Args:
            vehicle_id: Vehicle identifier (e.g., 'vehicle_1')
            
        Returns:
            JID string (e.g., 'vehicle1@local')
        """
        # Extract number from vehicle_id
        import re
        match = re.search(r'\d+', vehicle_id)
        if match:
            num = match.group()
            return f"vehicle{num}@local"
        return f"{vehicle_id}@local"
    
    def get_passenger_jid(self, passenger_id: str) -> str:
        """
        Map passenger_id to JID for messaging.
        
        Args:
            passenger_id: Passenger identifier
            
        Returns:
            JID string
        """
        # Passenger IDs can be complex, just ensure @local suffix
        if '@' not in passenger_id:
            return f"{passenger_id}@local"
        return passenger_id