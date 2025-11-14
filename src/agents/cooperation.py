"""
Vehicle Cooperation System
Enables vehicles to communicate and coordinate with each other
"""
import asyncio
from typing import List, Dict, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


class VehicleCoordinator:
    """
    Manages cooperation between vehicles
    Prevents multiple vehicles from responding to same station
    Enables convoy formation and load balancing
    """
    
    def __init__(self):
        self.vehicle_intentions = {}  # vehicle_id -> {'target_station': str, 'eta': datetime}
        self.station_assignments = defaultdict(set)  # station_id -> set of vehicle_ids
        self.vehicle_positions = {}  # vehicle_id -> (x, y)
        self.vehicle_capacities = {}  # vehicle_id -> current_passengers / max_capacity
        self.cooperation_history = []  # Track cooperation events
        
    def announce_intention(self, vehicle_id: str, target_station: str, eta: datetime, 
                          current_pos: Tuple[int, int], capacity_ratio: float):
        """
        Vehicle announces intention to service a station
        Returns: (should_proceed, reason, alternative_station)
        """
        self.vehicle_intentions[vehicle_id] = {
            'target_station': target_station,
            'eta': eta,
            'announced_at': datetime.now()
        }
        self.vehicle_positions[vehicle_id] = current_pos
        self.vehicle_capacities[vehicle_id] = capacity_ratio
        
        # Check if station already has enough coverage
        assigned = self.station_assignments[target_station]
        
        if len(assigned) == 0:
            # No one assigned yet, proceed
            self.station_assignments[target_station].add(vehicle_id)
            return (True, "first_responder", None)
        
        elif len(assigned) == 1:
            # One vehicle already assigned
            other_vehicle = list(assigned)[0]
            other_info = self.vehicle_intentions.get(other_vehicle)
            
            if not other_info:
                # Other vehicle info lost, allow this one
                self.station_assignments[target_station].add(vehicle_id)
                return (True, "replacement", None)
            
            # Compare ETAs - allow if this vehicle is significantly faster
            my_eta = eta
            their_eta = other_info['eta']
            
            if my_eta < their_eta - timedelta(minutes=3):
                # This vehicle is much faster
                self.station_assignments[target_station].add(vehicle_id)
                return (True, "faster_arrival", None)
            else:
                # Other vehicle is already handling it
                alternative = self._find_alternative_station(current_pos, target_station)
                return (False, "already_covered", alternative)
        
        else:
            # Multiple vehicles assigned - definitely covered
            alternative = self._find_alternative_station(current_pos, target_station)
            return (False, "overcrowded", alternative)
    
    def _find_alternative_station(self, current_pos: Tuple[int, int], 
                                  avoid_station: str) -> str:
        """Find an alternative station that needs service"""
        # Find stations with low coverage
        underserved = []
        for station_id, assigned_vehicles in self.station_assignments.items():
            if station_id != avoid_station and len(assigned_vehicles) == 0:
                underserved.append(station_id)
        
        if underserved:
            # Return closest underserved station
            return underserved[0]  # Simplified - could calculate actual distance
        
        return None
    
    def release_intention(self, vehicle_id: str):
        """Vehicle cancels its intention (breakdown, reroute, etc.)"""
        if vehicle_id in self.vehicle_intentions:
            target = self.vehicle_intentions[vehicle_id]['target_station']
            self.station_assignments[target].discard(vehicle_id)
            del self.vehicle_intentions[vehicle_id]
    
    def update_position(self, vehicle_id: str, position: Tuple[int, int]):
        """Update vehicle position for coordination"""
        self.vehicle_positions[vehicle_id] = position
    
    def find_nearby_vehicles(self, position: Tuple[int, int], radius: int = 5) -> List[str]:
        """Find vehicles within radius of position"""
        nearby = []
        px, py = position
        
        for vehicle_id, (vx, vy) in self.vehicle_positions.items():
            distance = abs(vx - px) + abs(vy - py)  # Manhattan distance
            if distance <= radius:
                nearby.append(vehicle_id)
        
        return nearby
    
    def form_convoy(self, vehicle_id: str, target_station: str) -> List[str]:
        """
        Find vehicles that could form a convoy to target station
        Returns list of vehicle IDs that should coordinate
        """
        if vehicle_id not in self.vehicle_positions:
            return [vehicle_id]
        
        my_pos = self.vehicle_positions[vehicle_id]
        nearby = self.find_nearby_vehicles(my_pos, radius=3)
        
        # Filter to vehicles heading same direction or idle
        convoy_members = [vehicle_id]
        
        for other_id in nearby:
            if other_id == vehicle_id:
                continue
                
            other_intent = self.vehicle_intentions.get(other_id)
            if not other_intent:
                # Idle vehicle - could join convoy
                convoy_members.append(other_id)
            elif other_intent['target_station'] == target_station:
                # Already heading same place
                convoy_members.append(other_id)
        
        if len(convoy_members) > 1:
            self.cooperation_history.append({
                'type': 'convoy_formed',
                'leader': vehicle_id,
                'members': convoy_members,
                'target': target_station,
                'timestamp': datetime.now()
            })
        
        return convoy_members
    
    def negotiate_load_balancing(self, station_id: str, demand: int) -> Dict[str, int]:
        """
        Distribute passenger load among vehicles heading to station
        Returns: {vehicle_id: recommended_passengers_to_take}
        """
        assigned = list(self.station_assignments[station_id])
        
        if not assigned:
            return {}
        
        # Get capacity info for each vehicle
        vehicle_capacities = {}
        for vehicle_id in assigned:
            if vehicle_id in self.vehicle_capacities:
                vehicle_capacities[vehicle_id] = self.vehicle_capacities[vehicle_id]
        
        if not vehicle_capacities:
            # Equal split if no capacity info
            per_vehicle = demand // len(assigned)
            return {vid: per_vehicle for vid in assigned}
        
        # Distribute based on available capacity
        total_available = sum(1 - ratio for ratio in vehicle_capacities.values())
        
        if total_available == 0:
            return {vid: 0 for vid in assigned}
        
        allocation = {}
        for vehicle_id, capacity_ratio in vehicle_capacities.items():
            available = 1 - capacity_ratio
            share = (available / total_available) * demand
            allocation[vehicle_id] = int(share)
        
        return allocation
    
    def get_coordination_stats(self) -> Dict:
        """Get statistics about vehicle cooperation"""
        convoys = [e for e in self.cooperation_history if e['type'] == 'convoy_formed']
        
        return {
            'active_vehicles': len(self.vehicle_positions),
            'total_intentions': len(self.vehicle_intentions),
            'stations_covered': len([s for s, v in self.station_assignments.items() if v]),
            'convoys_formed': len(convoys),
            'avg_station_coverage': sum(len(v) for v in self.station_assignments.values()) / max(len(self.station_assignments), 1)
        }
    
    def cleanup_stale_intentions(self, max_age_minutes: int = 10):
        """Remove old intentions that are no longer valid"""
        now = datetime.now()
        stale = []
        
        for vehicle_id, info in self.vehicle_intentions.items():
            age = (now - info['announced_at']).total_seconds() / 60
            if age > max_age_minutes:
                stale.append(vehicle_id)
        
        for vehicle_id in stale:
            self.release_intention(vehicle_id)


class CooperativeMessageProtocol:
    """
    Message types and handlers for vehicle-to-vehicle communication
    """
    
    MESSAGE_TYPES = {
        'INTENTION_ANNOUNCE': 'intention_announce',
        'CONVOY_INVITE': 'convoy_invite',
        'CONVOY_ACCEPT': 'convoy_accept',
        'LOAD_BALANCE': 'load_balance',
        'POSITION_UPDATE': 'position_update',
        'HELP_REQUEST': 'help_request',
        'HELP_RESPONSE': 'help_response'
    }
    
    @staticmethod
    def create_intention_message(vehicle_id: str, target_station: str, eta: datetime):
        """Create message announcing intention"""
        return {
            'type': CooperativeMessageProtocol.MESSAGE_TYPES['INTENTION_ANNOUNCE'],
            'vehicle_id': vehicle_id,
            'target_station': target_station,
            'eta': eta.isoformat(),
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def create_convoy_invite(leader_id: str, target_station: str, members: List[str]):
        """Create message inviting vehicles to form convoy"""
        return {
            'type': CooperativeMessageProtocol.MESSAGE_TYPES['CONVOY_INVITE'],
            'leader': leader_id,
            'target_station': target_station,
            'invited_members': members,
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def create_help_request(vehicle_id: str, problem: str, position: Tuple[int, int]):
        """Create message requesting help from nearby vehicles"""
        return {
            'type': CooperativeMessageProtocol.MESSAGE_TYPES['HELP_REQUEST'],
            'vehicle_id': vehicle_id,
            'problem': problem,
            'position': position,
            'timestamp': datetime.now().isoformat()
        }
