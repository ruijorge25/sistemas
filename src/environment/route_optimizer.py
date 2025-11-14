"""
Route optimization and dynamic adaptation for vehicles
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque

from ..environment.city import Position, Route

class RouteOptimizer:
    """Optimizes and adapts vehicle routes dynamically"""
    
    def __init__(self, city):
        self.city = city
        self.route_cache = {}  # Cache of calculated routes
        
    def calculate_optimal_route(self, start: Position, end: Position, 
                              current_traffic: Dict[Position, float]) -> List[Position]:
        """Calculate optimal route considering traffic using A* algorithm"""
        
        # A* pathfinding
        def heuristic(pos1: Position, pos2: Position) -> float:
            return pos1.distance_to(pos2)
        
        def get_neighbors(pos: Position) -> List[Position]:
            """Get valid neighboring positions"""
            neighbors = []
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]:
                new_x = pos.x + dx
                new_y = pos.y + dy
                
                if 0 <= new_x < self.city.grid_size[0] and 0 <= new_y < self.city.grid_size[1]:
                    neighbors.append(Position(new_x, new_y))
            
            return neighbors
        
        def get_cost(pos: Position) -> float:
            """Get movement cost considering traffic"""
            base_cost = 1.0
            traffic_level = current_traffic.get(pos, 0.5)
            return base_cost * (1 + traffic_level * 2)  # Traffic increases cost up to 3x
        
        # A* implementation
        open_set = {start}
        came_from = {}
        
        g_score = {start: 0}
        f_score = {start: heuristic(start, end)}
        
        while open_set:
            # Get node with lowest f_score
            current = min(open_set, key=lambda pos: f_score.get(pos, float('inf')))
            
            if current == end:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                path.reverse()
                return path
            
            open_set.remove(current)
            
            for neighbor in get_neighbors(current):
                tentative_g_score = g_score[current] + get_cost(neighbor)
                
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, end)
                    
                    if neighbor not in open_set:
                        open_set.add(neighbor)
        
        # No path found, return direct line
        return [start, end]
    
    def should_reroute(self, vehicle_agent, current_traffic: Dict[Position, float]) -> bool:
        """Determine if vehicle should reroute based on conditions"""
        
        # Check traffic ahead
        next_position = vehicle_agent.next_station
        if not next_position:
            return False
        
        traffic_ahead = current_traffic.get(next_position, 0.5)
        
        # Reroute if heavy traffic (> 0.7)
        if traffic_ahead > 0.7:
            return True
        
        # Check if there's high demand at other stations
        # (would be provided by coordinator)
        high_demand_stations = getattr(vehicle_agent, 'high_demand_stations', [])
        
        if high_demand_stations and len(vehicle_agent.passengers) < vehicle_agent.capacity * 0.5:
            # Vehicle is less than 50% full and there's high demand elsewhere
            return True
        
        return False
    
    def find_alternative_route(self, vehicle_agent, avoid_positions: List[Position],
                              target_stations: List[Position]) -> Optional[Route]:
        """Find alternative route avoiding congested areas"""
        
        current_pos = vehicle_agent.current_position
        
        # Find nearest high-demand station not in avoid list
        best_station = None
        best_score = -1
        
        for station_pos in target_stations:
            if station_pos in avoid_positions:
                continue
            
            # Score based on distance and demand
            distance = current_pos.distance_to(station_pos)
            
            # Get demand level (would be provided by coordinator)
            demand_level = getattr(vehicle_agent, 'station_demands', {}).get(station_pos, 0)
            
            # Score: prioritize closer stations with higher demand
            score = demand_level / (distance + 1)  # +1 to avoid division by zero
            
            if score > best_score:
                best_score = score
                best_station = station_pos
        
        if best_station:
            # Calculate route to high-demand station
            path = self.calculate_optimal_route(
                current_pos,
                best_station,
                self.city.traffic_conditions
            )
            
            # Create new route
            new_route = Route(
                id=f"dynamic_{vehicle_agent.vehicle_id}_{datetime.now().timestamp()}",
                stations=[current_pos] + path + [best_station],
                vehicle_type=vehicle_agent.vehicle_type
            )
            
            return new_route
        
        return None
    
    def optimize_station_sequence(self, stations: List[Position], 
                                 current_position: Position) -> List[Position]:
        """Optimize the sequence of stations to visit (TSP-like problem)"""
        
        if len(stations) <= 2:
            return stations
        
        # Greedy nearest-neighbor algorithm
        unvisited = set(stations)
        route = [current_position]
        current = current_position
        
        while unvisited:
            # Find nearest unvisited station
            nearest = min(unvisited, key=lambda s: current.distance_to(s))
            route.append(nearest)
            unvisited.remove(nearest)
            current = nearest
        
        return route[1:]  # Exclude starting position
    
    def estimate_travel_time(self, route: List[Position], 
                           current_traffic: Dict[Position, float],
                           vehicle_speed: float) -> float:
        """Estimate travel time for a route considering traffic"""
        
        total_time = 0.0
        
        for i in range(len(route) - 1):
            current_pos = route[i]
            next_pos = route[i + 1]
            
            distance = current_pos.distance_to(next_pos)
            traffic_level = current_traffic.get(next_pos, 0.5)
            
            # Speed is reduced by traffic
            effective_speed = vehicle_speed * (1 - traffic_level * 0.5)
            
            time_segment = distance / max(effective_speed, 0.1)  # Avoid division by zero
            total_time += time_segment
        
        return total_time
    
    def find_meeting_point(self, pos1: Position, pos2: Position) -> Position:
        """Find optimal meeting point between two positions"""
        
        # Simple midpoint for now
        mid_x = (pos1.x + pos2.x) // 2
        mid_y = (pos1.y + pos2.y) // 2
        
        return Position(mid_x, mid_y)
    
    def can_serve_passenger(self, vehicle_position: Position, vehicle_route: Route,
                           passenger_origin: Position, passenger_destination: Position) -> Tuple[bool, float]:
        """Check if vehicle can serve passenger and calculate detour cost"""
        
        # Check if passenger origin and destination are near the route
        route_stations = vehicle_route.stations
        
        # Find nearest station to passenger origin
        nearest_to_origin = min(route_stations, 
                               key=lambda s: s.distance_to(passenger_origin))
        dist_to_origin = nearest_to_origin.distance_to(passenger_origin)
        
        # Find nearest station to passenger destination
        nearest_to_dest = min(route_stations,
                             key=lambda s: s.distance_to(passenger_destination))
        dist_to_dest = nearest_to_dest.distance_to(passenger_destination)
        
        # Maximum acceptable detour distance
        max_detour = 5.0  # grid units
        
        if dist_to_origin <= max_detour and dist_to_dest <= max_detour:
            # Calculate detour cost
            detour_cost = dist_to_origin + dist_to_dest
            return True, detour_cost
        
        return False, float('inf')


class DynamicRouteAdapter:
    """Manages dynamic route adaptation for a vehicle"""
    
    def __init__(self, vehicle_agent, optimizer: RouteOptimizer):
        self.vehicle = vehicle_agent
        self.optimizer = optimizer
        self.adaptation_history = deque(maxlen=10)
        self.last_adaptation_time = None
        
    async def evaluate_and_adapt(self):
        """Evaluate current situation and adapt route if necessary"""
        
        # Don't adapt too frequently
        if self.last_adaptation_time:
            time_since_last = (datetime.now() - self.last_adaptation_time).total_seconds()
            if time_since_last < 30:  # Wait at least 30 seconds
                return False
        
        # Check if rerouting is needed
        should_reroute = self.optimizer.should_reroute(
            self.vehicle,
            self.vehicle.city.traffic_conditions
        )
        
        if should_reroute:
            await self.adapt_route()
            return True
        
        return False
    
    async def adapt_route(self):
        """Adapt the vehicle's route based on current conditions"""
        
        # Get high-demand stations
        high_demand_stations = getattr(self.vehicle, 'high_demand_stations', [])
        
        # Get congested positions to avoid
        congested_positions = [
            pos for pos, traffic in self.vehicle.city.traffic_conditions.items()
            if traffic > 0.7
        ]
        
        # Find alternative route
        new_route = self.optimizer.find_alternative_route(
            self.vehicle,
            congested_positions,
            high_demand_stations if high_demand_stations else self.vehicle.city.stations
        )
        
        if new_route:
            old_route_id = self.vehicle.assigned_route.id
            self.vehicle.assigned_route = new_route
            self.vehicle.next_station = new_route.stations[1] if len(new_route.stations) > 1 else None
            
            self.last_adaptation_time = datetime.now()
            self.adaptation_history.append({
                'time': datetime.now(),
                'old_route': old_route_id,
                'new_route': new_route.id,
                'reason': 'traffic_or_demand'
            })
            
            print(f"🔄 Vehicle {self.vehicle.vehicle_id} adapted route from {old_route_id} to {new_route.id}")
            
            # Notify nearby stations about route change
            await self.notify_route_change(new_route)
            
            return True
        
        return False
    
    async def notify_route_change(self, new_route: Route):
        """Notify stations about route change"""
        from ..config.settings import MESSAGE_TYPES
        
        station_agents = getattr(self.vehicle, 'station_agents_at_position', [])
        
        for station_jid in station_agents:
            await self.vehicle.send_message(
                station_jid,
                {
                    'vehicle_id': self.vehicle.vehicle_id,
                    'new_route': {
                        'id': new_route.id,
                        'stations': [{'x': s.x, 'y': s.y} for s in new_route.stations]
                    },
                    'reason': 'dynamic_adaptation'
                },
                MESSAGE_TYPES['ROUTE_UPDATE']
            )
    
    def get_adaptation_stats(self) -> Dict[str, Any]:
        """Get statistics about route adaptations"""
        return {
            'total_adaptations': len(self.adaptation_history),
            'last_adaptation': self.last_adaptation_time.isoformat() if self.last_adaptation_time else None,
            'adaptations': list(self.adaptation_history)
        }