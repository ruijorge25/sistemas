"""
Traffic Manager for handling rail blocking and road overtaking
"""
from typing import Dict, Set, Tuple, Optional
from ..environment.city import Position

class TrafficManager:
    """Manages traffic flow, blocking on rails, and overtaking on roads"""
    
    def __init__(self):
        # Track vehicles at each position with their direction and type
        # position -> {vehicle_id: {'type': str, 'direction': tuple, 'status': str}}
        self.position_occupancy: Dict[Tuple[int, int], Dict[str, Dict]] = {}
        
        # Track blocked positions on tram rails
        self.blocked_rails: Set[Tuple[int, int]] = set()
    
    def register_vehicle_position(self, vehicle_id: str, position: Position, 
                                  vehicle_type: str, direction: Tuple[int, int],
                                  is_broken: bool = False):
        """Register a vehicle's current position and direction"""
        pos_tuple = (position.x, position.y)
        
        if pos_tuple not in self.position_occupancy:
            self.position_occupancy[pos_tuple] = {}
        
        self.position_occupancy[pos_tuple][vehicle_id] = {
            'type': vehicle_type,
            'direction': direction,
            'broken': is_broken
        }
        
        # If it's a broken tram, block the rail
        if vehicle_type == 'tram' and is_broken:
            self.blocked_rails.add(pos_tuple)
            print(f"🚫 Rail blocked at {pos_tuple} due to broken tram {vehicle_id}")
    
    def unregister_vehicle_position(self, vehicle_id: str, position: Position):
        """Remove a vehicle from a position"""
        pos_tuple = (position.x, position.y)
        
        if pos_tuple in self.position_occupancy:
            vehicle_info = self.position_occupancy[pos_tuple].get(vehicle_id)
            
            if vehicle_info:
                # Unblock rail if it was a broken tram
                if vehicle_info['type'] == 'tram' and vehicle_info['broken']:
                    self.blocked_rails.discard(pos_tuple)
                    print(f"✅ Rail unblocked at {pos_tuple}")
                
                del self.position_occupancy[pos_tuple][vehicle_id]
            
            # Clean up empty positions
            if not self.position_occupancy[pos_tuple]:
                del self.position_occupancy[pos_tuple]
    
    def can_move_to_position(self, vehicle_id: str, target_position: Position,
                           vehicle_type: str, direction: Tuple[int, int]) -> bool:
        """
        Check if a vehicle can move to a target position.
        
        TRAMS (Rails):
        - Cannot move if blocked by broken tram
        - Cannot move if another tram is moving in same direction
        - CAN move if trams are moving in opposite directions
        
        BUSES (Roads):
        - Can always overtake (multiple buses can share same cell)
        - Can move in opposite directions
        """
        pos_tuple = (target_position.x, target_position.y)
        
        # Check if position is occupied
        if pos_tuple not in self.position_occupancy:
            return True  # Empty position, can move
        
        vehicles_at_position = self.position_occupancy[pos_tuple]
        
        # TRAM LOGIC (Rail blocking)
        if vehicle_type == 'tram':
            # Check if rail is blocked by broken tram
            if pos_tuple in self.blocked_rails:
                return False
            
            # Check for other trams
            for other_id, other_info in vehicles_at_position.items():
                if other_id == vehicle_id:
                    continue
                
                if other_info['type'] == 'tram':
                    # Check if moving in same direction
                    if self._same_direction(direction, other_info['direction']):
                        return False  # Blocked by tram in same direction
                    # Opposite direction is OK
            
            return True
        
        # BUS LOGIC (Road overtaking)
        elif vehicle_type == 'bus':
            # Buses can always overtake on roads
            return True
        
        # Maintenance vehicles behave like buses
        return True
    
    def _same_direction(self, dir1: Tuple[int, int], dir2: Tuple[int, int]) -> bool:
        """Check if two direction vectors are in the same general direction"""
        if dir1 == (0, 0) or dir2 == (0, 0):
            return False  # Stationary vehicles don't block
        
        # Calculate dot product to determine if directions are similar
        # Positive dot product = same general direction
        # Negative = opposite direction
        # Zero = perpendicular
        dot_product = dir1[0] * dir2[0] + dir1[1] * dir2[1]
        
        return dot_product > 0
    
    def get_vehicles_at_position(self, position: Position) -> Dict[str, Dict]:
        """Get all vehicles at a specific position"""
        pos_tuple = (position.x, position.y)
        return self.position_occupancy.get(pos_tuple, {}).copy()
    
    def is_position_blocked(self, position: Position, vehicle_type: str) -> bool:
        """Quick check if a position is blocked for a vehicle type"""
        pos_tuple = (position.x, position.y)
        
        # For trams, check if rail is blocked
        if vehicle_type == 'tram':
            return pos_tuple in self.blocked_rails
        
        # Buses can always move (overtaking)
        return False
    
    def repair_vehicle(self, vehicle_id: str, position: Position):
        """Mark a vehicle as repaired, unblocking any rails"""
        pos_tuple = (position.x, position.y)
        
        if pos_tuple in self.position_occupancy:
            if vehicle_id in self.position_occupancy[pos_tuple]:
                self.position_occupancy[pos_tuple][vehicle_id]['broken'] = False
                
                # Unblock rail
                if pos_tuple in self.blocked_rails:
                    self.blocked_rails.discard(pos_tuple)
                    print(f"✅ Rail unblocked at {pos_tuple} - vehicle repaired")
    
    def get_traffic_status(self) -> Dict:
        """Get overall traffic status"""
        total_positions = len(self.position_occupancy)
        total_vehicles = sum(len(vehicles) for vehicles in self.position_occupancy.values())
        blocked_rails_count = len(self.blocked_rails)
        
        # Count by vehicle type
        buses = 0
        trams = 0
        maintenance = 0
        
        for vehicles in self.position_occupancy.values():
            for info in vehicles.values():
                if info['type'] == 'bus':
                    buses += 1
                elif info['type'] == 'tram':
                    trams += 1
                else:
                    maintenance += 1
        
        return {
            'occupied_positions': total_positions,
            'total_vehicles': total_vehicles,
            'blocked_rails': blocked_rails_count,
            'buses_on_road': buses,
            'trams_on_rail': trams,
            'maintenance_vehicles': maintenance
        }
