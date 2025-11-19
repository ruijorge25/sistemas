"""
Vehicle agents (buses and trams) for the transportation system - PURE SPADE
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .base_agent import BaseTransportAgent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from ..environment.city import Position, Route
from ..environment.route_optimizer import RouteOptimizer, DynamicRouteAdapter
from ..config.settings import MESSAGE_TYPES, SIMULATION_CONFIG, DEBUG
from ..ml.learning import QLearningRouter, ReinforcementLearner
from ..protocols.contract_net import ContractNetParticipant
from .cooperation import VehicleCoordinator

@dataclass
class PassengerInfo:
    id: str
    origin: Position
    destination: Position
    boarding_time: datetime
    target_arrival_time: datetime

class VehicleAgent(BaseTransportAgent):
    """Agent representing a bus or tram vehicle"""
    
    # Shared vehicle coordinator for all vehicles (class variable)
    coordinator = VehicleCoordinator()
    
    def __init__(self, jid: str, password: str, vehicle_id: str, vehicle_type: str, 
                 assigned_route: Route, city, initial_passengers=None, metrics_collector=None, **kwargs):
        super().__init__(jid, password, f"{vehicle_type}_vehicle", metrics_collector=metrics_collector)
        
        self.vehicle_id = vehicle_id
        self.vehicle_type = vehicle_type  # 'bus' or 'tram'
        self.assigned_route = assigned_route
        self.city = city
        
        # Vehicle state
        self.current_position = assigned_route.stations[0] if assigned_route.stations else Position(0, 0)
        self.current_station_index = 0
        
        # ✅ FIX: Track FLOAT position internally to avoid int() truncation bug
        # Without this, vehicles get stuck because int(0.5) = 0 → never moves!
        self._float_x = float(self.current_position.x)
        self._float_y = float(self.current_position.y)
        
        # Set capacity based on vehicle type or kwargs (for tests)
        vehicle_config = SIMULATION_CONFIG['vehicle']
        if vehicle_type == 'bus':
            default_capacity = vehicle_config['bus_capacity']
        else:
            default_capacity = vehicle_config['tram_capacity']
        
        # Allow capacity override from tests/validator (kwargs)
        self.capacity = kwargs.get('capacity', default_capacity)
        
        # Passenger management (STEP 3: Clean structure)
        # self.passengers - legacy list for backward compatibility
        self.passengers = initial_passengers if initial_passengers else []
        # NEW: Dict-based tracking for robust boarding/alighting
        self.passengers_onboard: Dict[str, Dict] = {}  # {passenger_id: {"destination": station_id}}
        self.occupancy = len(self.passengers)  # Current passenger count
        
        self.fuel_level = SIMULATION_CONFIG['vehicle']['fuel_capacity']
        
        # PASSO 1: Estado explícito do veículo (ciclo de vida)
        self.state = "EN_ROUTE"  # Estados: "EN_ROUTE", "AT_STATION", "BROKEN"
        self.is_broken = False
        self.breakdown_type = None  # 'tire', 'engine', or 'tow'
        self.breakdown_time = None  # When breakdown occurred
        self.maintenance_requested = False
        self.maintenance_crews_jids = []  # Will be set by simulation setup (PASSO 4)
        
        # PASSO 5: Boarding state machine
        self.current_station_id = None  # Current station (when AT_STATION)
        self.boarding_in_progress = False
        self.boarding_ticks = 0
        self.MAX_BOARDING_TICKS = 3  # Ticks to wait for boarding
        
        # Movement and scheduling
        # CRITICAL FIX: Ensure next_station is NEVER None
        if len(assigned_route.stations) > 1:
            self.next_station = self.assigned_route.stations[1]
        else:
            # Fallback: If route has only 1 station, use it (vehicle will stay there)
            self.next_station = self.assigned_route.stations[0]
        self.estimated_arrival_time = datetime.now() + timedelta(minutes=5)
        self.speed_modifier = 1.0  # Affected by traffic
        
        # Performance tracking
        self.on_time_arrivals = 0
        self.total_arrivals = 0
        self.passengers_served = 0
        self.total_distance_traveled = 0.0  # For analytics - already present!
        self.total_passengers_transported = 0  # For analytics - already present!
        
        # Route optimization
        self.route_optimizer = RouteOptimizer(city)
        self.route_adapter = None  # Will be initialized in setup
        
        # Q-Learning for intelligent routing
        self.q_learner = QLearningRouter(
            num_stations=len(city.stations),
            learning_rate=0.1,
            discount=0.9,
            epsilon=0.2
        )
        self.last_state = None
        self.last_action = None
        self.rl_learner = ReinforcementLearner(learning_rate=0.1)
        self.ml_enabled = True
        
        # Contract Net Protocol
        self.cnp_participant = ContractNetParticipant(self)
        
        # Dynamic events
        self.event_manager = None  # Will be set by coordinator
        self.traffic_modifier = 1.0
        self.route_adaptations = 0
        
        # Vehicle cooperation
        self.convoy_members = set()  # IDs of vehicles in convoy
        self.is_in_convoy = False
    
    # ========================================
    # PASSO 7: INVARIANTS & HELPERS
    # ========================================
    
    def check_invariants(self):
        """PASSO 7: Verify vehicle invariants (only when DEBUG=True)"""
        if not DEBUG:
            return
        
        # Invariant 1: occupancy matches passengers_onboard
        assert self.occupancy == len(self.passengers_onboard), \
            f"[{self.vehicle_id}] INVARIANT VIOLATION: occupancy={self.occupancy} != passengers_onboard={len(self.passengers_onboard)}"
        
        # Invariant 2: occupancy never exceeds capacity
        assert self.occupancy <= self.capacity, \
            f"[{self.vehicle_id}] INVARIANT VIOLATION: occupancy={self.occupancy} > capacity={self.capacity}"
        
        # Invariant 3: state is valid
        valid_states = ["EN_ROUTE", "AT_STATION", "BROKEN"]
        assert self.state in valid_states, \
            f"[{self.vehicle_id}] INVARIANT VIOLATION: invalid state={self.state}"
        
        # Invariant 4: if BROKEN, is_broken must be True
        if self.state == "BROKEN":
            assert self.is_broken, \
                f"[{self.vehicle_id}] INVARIANT VIOLATION: state=BROKEN but is_broken=False"
    
    def get_next_station(self) -> Position:
        """PASSO 7: Safe helper to get next station (prevents direct route manipulation)"""
        if not self.assigned_route or not self.assigned_route.stations:
            return Position(0, 0)
        return self.assigned_route.stations[self.current_station_index]
        
    async def setup(self):
        """Setup vehicle-specific behaviours"""
        await super().setup()
        
        # Initialize route adapter
        self.route_adapter = DynamicRouteAdapter(self, self.route_optimizer)
        
        # Add unified behaviour for vehicle operations
        self.add_behaviour(self.VehicleMainBehaviour())
    
    async def handle_message(self, msg: Message):
        """
        PURE SPADE message handler - routes incoming messages to appropriate handlers
        """
        await super().handle_message(msg)  # Log message
        
        msg_type = msg.metadata.get('type') if msg.metadata else None
        
        try:
            import json
            body = json.loads(msg.body) if isinstance(msg.body, str) else msg.body
            
            if msg_type == MESSAGE_TYPES['BOARDING_LIST']:
                self.handle_boarding_list(body)
            elif msg_type == MESSAGE_TYPES['MAINTENANCE_COMPLETED']:
                await self.handle_maintenance_completed(msg)
            elif msg_type == MESSAGE_TYPES['CONTRACT_NET_CFP']:
                await self.cnp_participant.handle_cfp(msg)
            elif msg_type == MESSAGE_TYPES.get('PASSENGER_REQUEST'):
                await self.handle_passenger_request(msg)
            elif msg_type == MESSAGE_TYPES['CONTRACT_NET_ACCEPT']:
                # Contract accepted - we won the bid
                await self.handle_contract_accepted(msg)
            elif msg_type == MESSAGE_TYPES['CONTRACT_NET_REJECT']:
                # Contract rejected - normal operation, silently continue
                pass
            else:
                print(f"⚠️ [{self.vehicle_id}] Unknown message type: {msg_type}")
        
        except Exception as e:
            print(f"❌ [{self.vehicle_id}] Error handling message: {e}")
            import traceback
            traceback.print_exc()
    
    class VehicleMainBehaviour(CyclicBehaviour):
        """
        PURE SPADE: Unified behaviour for all vehicle operations
        - Messages received automatically via MessageReceiverBehaviour (base_agent)
        - Update state (movement, boarding, breakdowns)
        - Handle all logic in one place
        """
        
        async def run(self):
            tick_rate = SIMULATION_CONFIG['simulation']['time_step']
            check_health_counter = 0
            route_adapt_counter = 0
            
            while True:
                try:
                    # STEP 1: Update vehicle state (movement, boarding, etc)
                    self.agent.update_vehicle_state()
                    
                    # STEP 2: Periodic health checks
                    check_health_counter += 1
                    if check_health_counter >= 50:  # Every ~10s with 0.2s tick
                        await self.agent.check_vehicle_health()
                        check_health_counter = 0
                    
                    # STEP 3: Route adaptation
                    route_adapt_counter += 1
                    if route_adapt_counter >= 100:  # Every ~20s
                        if self.agent.route_adapter and not self.agent.is_broken:
                            await self.agent.route_adapter.evaluate_and_adapt()
                        route_adapt_counter = 0
                    
                    # STEP 4: Tick rate control
                    await asyncio.sleep(tick_rate)
                    
                except Exception as e:
                    print(f"💥 [{self.agent.vehicle_id}] EXCEPTION: {type(e).__name__}: {e}")
                    print(f"   State: {self.agent.state}, next_station: {self.agent.next_station}")
                    import traceback
                    traceback.print_exc()
                    if str(e).find("NoneType") != -1:
                        self.agent._recover_next_station()
                    await asyncio.sleep(1)
    
    # ========================================
    # TICK-BASED STATE UPDATE (AUTONOMOUS BEHAVIOR)
    # ========================================
    
    def update_vehicle_state(self):
        """
        Update vehicle state every tick - AUTONOMOUS MOVEMENT (PASSO 1: respects state)
        This method ALWAYS runs, regardless of messages received.
        Vehicle never stops moving unless explicitly broken.
        """
        # CRITICAL: Validate next_station before any state updates
        if not self.next_station:
            print(f"⚠️ [{self.vehicle_id}] WARNING: next_station is None at tick start!")
            self._recover_next_station()
            if not self.next_station:
                print(f"❌ [{self.vehicle_id}] FATAL: Cannot recover next_station. Vehicle stopping.")
                return
        
        # Increment tick counter
        self.current_tick += 1
        
        # PASSO 7: Check invariants every 50 ticks (if DEBUG=True)
        if DEBUG and self.current_tick % 50 == 0:
            self.check_invariants()
        
        # DIAGNOSTIC: Log state periodically
        if self.current_tick % 10 == 0:
            print(f"🔍 [{self.vehicle_id}] Tick #{self.current_tick}: state={self.state}, broken={self.is_broken}, fuel={self.fuel_level:.1f}, next_station={self.next_station}, pos=({self.current_position.x},{self.current_position.y})")
        
        # PASSO 1: If broken, vehicle is COMPLETELY STOPPED
        if self.is_broken or self.state == "BROKEN":
            if self.current_tick % 20 == 0:
                print(f"🚨 [{self.vehicle_id}] IMMOBILIZED: state={self.state}, breakdown_type={self.breakdown_type}, passengers_stuck={self.occupancy}")
            return  # Don't move, don't consume fuel
        
        # PASSO 5: State machine for EN_ROUTE vs AT_STATION
        if self.state == "EN_ROUTE":
            self._advance_along_route()
            # Check if arrived at station
            if self._has_arrived_at_station():
                asyncio.create_task(self._on_arrival_to_station())
        
        elif self.state == "AT_STATION":
            self._handle_station_stop_logic()
    
    def _advance_along_route(self):
        """PASSO 5: Move vehicle along route (only when EN_ROUTE)"""
        # 🔧 AUTO-REFUEL: Garante que veículo NUNCA para por falta de fuel
        if self.fuel_level < 30.0:
            old_fuel = self.fuel_level
            self.fuel_level = 100.0
            if old_fuel < 20.0:  # Log when getting low
                print(f"⛽ [{self.vehicle_id}] AUTO-REFUEL: {old_fuel:.1f}% → 100%")
        
        # Check if next_station is valid
        if not self.next_station:
            self._recover_next_station()
            if not self.next_station:  # Still None after recovery
                return
        
        # Check traffic conditions
        if self.event_manager:
            pos = (self.current_position.x, self.current_position.y)
            self.traffic_modifier = self.event_manager.get_traffic_modifier(pos)
        
        # MOVE (this is the core - always happens)
        self._move_step()
    
    def _recover_next_station(self):
        """Recover next_station if it became None"""
        print(f"❌ [{self.vehicle_id}] next_station is None! Recovering...")
        if self.assigned_route and len(self.assigned_route.stations) > 0:
            # Find first station different from current position
            for idx, station in enumerate(self.assigned_route.stations):
                if station.x != self.current_position.x or station.y != self.current_position.y:
                    self.next_station = station
                    self.current_station_index = idx
                    print(f"✅ [{self.vehicle_id}] Recovered: next_station=({station.x},{station.y})")
                    return
            # All stations same position (shouldn't happen)
            self.next_station = self.assigned_route.stations[0]
            print(f"⚠️ [{self.vehicle_id}] All stations same, using first")
    
    def _move_step(self):
        """Execute one movement step towards next_station"""
        # CRITICAL: Verify next_station is valid BEFORE moving
        if not self.next_station:
            print(f"❌ [{self.vehicle_id}] CRITICAL: next_station is None in _move_step()!")
            self._recover_next_station()
            if not self.next_station:
                print(f"❌ [{self.vehicle_id}] FATAL: Cannot recover next_station. Vehicle STOPPED.")
                return
        
        # Consume fuel
        self.fuel_level -= SIMULATION_CONFIG['vehicle']['fuel_consumption_rate']
        
        # Calculate movement
        distance_to_next = self.current_position.distance_to(self.next_station)
        movement_speed = SIMULATION_CONFIG['vehicle']['speed'] * self.speed_modifier
        
        if distance_to_next <= movement_speed:
            # Arrived at station (will be handled in next check)
            self.current_position = self.next_station
            self._float_x = float(self.next_station.x)
            self._float_y = float(self.next_station.y)
            self.total_distance_traveled += distance_to_next
        else:
            # Move towards station using FLOAT position (avoids int truncation bug)
            dx = self.next_station.x - self._float_x
            dy = self.next_station.y - self._float_y
            distance = (dx**2 + dy**2)**0.5
            
            if distance > 0:
                move_x = (dx / distance) * movement_speed
                move_y = (dy / distance) * movement_speed
                
                self.total_distance_traveled += movement_speed
                
                # ✅ FIX: Update FLOAT position first, then convert to int
                self._float_x += move_x
                self._float_y += move_y
                self.current_position = Position(round(self._float_x), round(self._float_y))
                
                # Log occasionally
                if round(self._float_x) % 3 == 0 and round(self._float_y) % 3 == 0:
                    print(f"🚗 {self.vehicle_id} at ({self._float_x:.1f},{self._float_y:.1f}) → ({round(self._float_x)},{round(self._float_y)}) towards ({self.next_station.x},{self.next_station.y})")
    
    def _has_arrived_at_station(self) -> bool:
        """Check if vehicle has arrived at next_station (STEP 3: Robust detection)"""
        if not self.next_station:
            return False
        # Use exact position match (already using int positions)
        return (self.current_position.x == self.next_station.x and 
                self.current_position.y == self.next_station.y)
    
    async def _on_arrival_to_station(self):
        """
        PASSO 5: Handle arrival at station - ROBUST COORDINATION
        1. Change state to AT_STATION
        2. Update current_station_id and next_station_id
        3. Alight passengers
        4. Send VEHICLE_ARRIVED to station
        5. Start boarding process
        """
        self.state = "AT_STATION"
        self.current_station_id = self._get_station_id_at_position(self.current_position)
        
        self.total_arrivals += 1
        current_time = datetime.now()
        
        if current_time <= self.estimated_arrival_time:
            self.on_time_arrivals += 1
        
        print(f"🚌 [{self.vehicle_id}] ARRIVED at {self.current_station_id} | occupancy={self.occupancy}/{self.capacity}")
        
        # STEP 1: Alight passengers who reached destination
        self._alight_passengers_at_station()
        
        # STEP 2: Notify station of arrival
        await self._send_vehicle_arrived_message()
        
        # STEP 3: Start boarding
        self.boarding_in_progress = True
        self.boarding_ticks = 0
    
    def _alight_passengers_at_station(self):
        """
        STEP 3: Alight passengers who reached their destination.
        Updates both passengers_onboard (dict) and legacy passengers (list).
        Also sends TRIP_COMPLETED to each passenger.
        """
        current_station_id = self._get_station_id_at_position(self.current_position)
        
        # Find passengers to alight
        alighting_pids = []
        for pid, info in list(self.passengers_onboard.items()):
            if info["destination"] == current_station_id:
                alighting_pids.append(pid)
        
        # Alight them
        for pid in alighting_pids:
            del self.passengers_onboard[pid]
            self.occupancy -= 1
            self.passengers_served += 1
            self.total_passengers_transported += 1
            
            # Send TRIP_COMPLETED to passenger (async)
            asyncio.create_task(self._send_trip_completed(pid, current_station_id))
        
        if alighting_pids:
            print(f"👋 [{self.vehicle_id}] {len(alighting_pids)} passengers alighted | occupancy={self.occupancy}/{self.capacity}")
        
        # Legacy: Also remove from self.passengers list
        passengers_to_remove = []
        for passenger in self.passengers:
            if hasattr(passenger, 'destination'):
                if (passenger.destination.x == self.current_position.x and 
                    passenger.destination.y == self.current_position.y):
                    passengers_to_remove.append(passenger)
        
        for passenger in passengers_to_remove:
            self.passengers.remove(passenger)
    
    async def _send_trip_completed(self, passenger_id: str, station_id: str):
        """Send TRIP_COMPLETED message to passenger"""
        try:
            passenger_jid = self.city.get_passenger_jid(passenger_id)
            await self.send_message(
                passenger_jid,
                {
                    "passenger_id": passenger_id,
                    "vehicle_id": self.vehicle_id,
                    "station_id": station_id
                },
                MESSAGE_TYPES['TRIP_COMPLETED']
            )
        except Exception as e:
            # Passenger might not exist (dict-based passenger) - not critical
            pass
    
    async def _send_vehicle_arrived_message(self):
        """
        STEP 3: Send VEHICLE_ARRIVED message to station.
        Station will respond with BOARDING_LIST.
        """
        try:
            current_station_id = self._get_station_id_at_position(self.current_position)
            station_jid = self.city.get_station_jid(current_station_id)
            
            await self.send_message(
                station_jid,
                {
                    "vehicle_id": self.vehicle_id,
                    "station_id": current_station_id,
                    "capacity": self.capacity,
                    "occupancy": self.occupancy,
                    "position": {"x": self.current_position.x, "y": self.current_position.y}
                },
                MESSAGE_TYPES['VEHICLE_ARRIVED']
            )
            print(f"📨 [{self.vehicle_id}] Sent VEHICLE_ARRIVED to {station_jid}")
        except Exception as e:
            print(f"⚠️ [{self.vehicle_id}] Failed to notify station: {e}")
    
    def _handle_station_stop_logic(self):
        """
        PASSO 5: Handle logic while stopped at station.
        Vehicle waits for boarding to complete before departing.
        """
        if self.boarding_in_progress:
            self.boarding_ticks += 1
            if self.boarding_ticks > self.MAX_BOARDING_TICKS:
                self.boarding_in_progress = False
                self._depart_from_station()
        else:
            # No boarding, depart immediately
            self._depart_from_station()
    
    def _depart_from_station(self):
        """PASSO 5: Depart from current station and continue route"""
        print(f"🚀 [{self.vehicle_id}] DEPARTING from {self.current_station_id} | occupancy={self.occupancy}/{self.capacity}")
        
        # Change state back to EN_ROUTE
        self.state = "EN_ROUTE"
        self.current_station_id = None
        
        # Advance to next station
        self._advance_to_next_station()
    
    def _get_station_id_at_position(self, position: Position) -> str:
        """Get station_id for a given position (heuristic)"""
        # Try to find in city.stations
        if self.city and hasattr(self.city, 'stations'):
            for idx, station_pos in enumerate(self.city.stations):
                if station_pos.x == position.x and station_pos.y == position.y:
                    return f"station_{idx}"
        # Fallback: Use position as ID
        return f"station_at_{position.x}_{position.y}"
    
    def _advance_to_next_station(self):
        """Move to next station in route (circular)"""
        old_index = self.current_station_index
        attempts = 0
        max_attempts = len(self.assigned_route.stations)
        
        while attempts < max_attempts:
            self.current_station_index = (self.current_station_index + 1) % len(self.assigned_route.stations)
            candidate_station = self.assigned_route.stations[self.current_station_index]
            
            if (candidate_station.x != self.current_position.x or 
                candidate_station.y != self.current_position.y):
                self.next_station = candidate_station
                break
            attempts += 1
        
        if attempts >= max_attempts:
            self.current_station_index = (old_index + 1) % len(self.assigned_route.stations)
            self.next_station = self.assigned_route.stations[self.current_station_index]
        
        # Update ETA
        distance_to_next = self.current_position.distance_to(self.next_station)
        travel_time_minutes = (distance_to_next / SIMULATION_CONFIG['vehicle']['speed']) * 2
        self.estimated_arrival_time = datetime.now() + timedelta(minutes=travel_time_minutes)
    
    # ========================================
    # OLD METHOD (kept for compatibility but not used in tick-based system)
    # ========================================
    
    async def move_towards_next_station(self):
        """Move the vehicle towards its next station"""
        if not self.next_station:
            print(f"⚠️ {self.vehicle_id} has no next_station!")
            return
        
        # Check if vehicle is broken or out of fuel
        if self.is_broken:
            # Don't spam logs - already logged in MovementBehaviour
            return
            
        # CRITICAL FIX: Check fuel BEFORE consuming
        if self.fuel_level <= 0.5:  # Safety margin for fuel
            print(f"⛽ [{self.vehicle_id}] OUT OF FUEL at ({self.current_position.x},{self.current_position.y}) - fuel={self.fuel_level:.2f}")
            # AUTO-REFUEL instead of breaking down
            self.fuel_level = 100.0
            print(f"⛽ [{self.vehicle_id}] EMERGENCY AUTO-REFUEL to 100%")
            return  # Skip this iteration, continue next time
            
        # Consume fuel
        self.fuel_level -= SIMULATION_CONFIG['vehicle']['fuel_consumption_rate']
        
        # DIAGNOSTIC: Warn when fuel getting low
        if self.fuel_level < 20 and int(self.fuel_level) % 5 == 0:  # Log at 20, 15, 10, 5
            print(f"⚠️ [{self.vehicle_id}] Low fuel warning: {self.fuel_level:.1f}%")
        
        # Check traffic conditions (uses event_manager internally)
        if hasattr(self.city, 'event_manager') and self.city.event_manager:
            location = (self.current_position.x, self.current_position.y)
            self.speed_modifier = self.city.event_manager.get_traffic_modifier(location)
        else:
            # Fallback to old method
            traffic_level = self.city.get_traffic_level(self.current_position)
            self.speed_modifier = max(0.3, 1.0 - traffic_level)
        
        # Calculate movement
        distance_to_next = self.current_position.distance_to(self.next_station)
        movement_speed = SIMULATION_CONFIG['vehicle']['speed'] * self.speed_modifier
        
        if distance_to_next <= movement_speed:
            # Arrived at station
            self.total_distance_traveled += distance_to_next
            await self.arrive_at_station()
        else:
            # Move towards station
            dx = self.next_station.x - self.current_position.x
            dy = self.next_station.y - self.current_position.y
            distance = (dx**2 + dy**2)**0.5
            
            if distance > 0:
                move_x = (dx / distance) * movement_speed
                move_y = (dy / distance) * movement_speed
                
                # Track distance for analytics
                self.total_distance_traveled += movement_speed
                
                # Create new Position object (frozen dataclass)
                new_x = self.current_position.x + move_x
                new_y = self.current_position.y + move_y
                self.current_position = Position(int(new_x), int(new_y))
                # Only log occasionally to reduce terminal spam
                if int(new_x) % 3 == 0 and int(new_y) % 3 == 0:
                    print(f"🚗 {self.vehicle_id} moving to ({int(new_x)},{int(new_y)}) towards ({self.next_station.x},{self.next_station.y})")
    
    async def arrive_at_station(self):
        """Handle arrival at a station"""
        self.current_position = self.next_station
        self.total_arrivals += 1
        
        # Check if on time
        current_time = datetime.now()
        if current_time <= self.estimated_arrival_time:
            self.on_time_arrivals += 1
        
        print(f"🚌 [{self.vehicle_id}] ARRIVED at station ({self.current_position.x},{self.current_position.y}) | passengers={len(self.passengers)}/{self.capacity}")
        
        # Handle passenger alighting BEFORE boarding
        await self.handle_passenger_alighting()
        
        # Notify station of arrival - CRITICAL for boarding
        station_agents = await self.get_station_agents_at_position(self.current_position)
        for station_agent in station_agents:
            await self.send_message(
                station_agent,
                {
                    'vehicle_id': self.vehicle_id,
                    'vehicle_type': self.vehicle_type,
                    'available_capacity': self.capacity - len(self.passengers),
                    'position': {'x': self.current_position.x, 'y': self.current_position.y}
                },
                MESSAGE_TYPES['VEHICLE_CAPACITY']
            )
            print(f"📤 [{self.vehicle_id}] sent VEHICLE_CAPACITY to {station_agent} (capacity: {self.capacity - len(self.passengers)})")
        
        # CRITICAL FIX: Move to NEXT DIFFERENT station in route
        old_index = self.current_station_index
        attempts = 0
        max_attempts = len(self.assigned_route.stations)
        
        while attempts < max_attempts:
            # Increment index
            self.current_station_index = (self.current_station_index + 1) % len(self.assigned_route.stations)
            candidate_station = self.assigned_route.stations[self.current_station_index]
            
            # Check if station is different from current position
            if (candidate_station.x != self.current_position.x or 
                candidate_station.y != self.current_position.y):
                self.next_station = candidate_station
                break
            
            attempts += 1
        
        # SAFETY: If all stations are the same (shouldn't happen), just use next index
        if attempts >= max_attempts:
            print(f"⚠️ [{self.vehicle_id}] WARNING: All route stations are identical! Using fallback.")
            self.current_station_index = (old_index + 1) % len(self.assigned_route.stations)
            self.next_station = self.assigned_route.stations[self.current_station_index]
        
        # DIAGNOSTIC: Log route progression
        print(f"➡️  [{self.vehicle_id}] Route: station {old_index} → {self.current_station_index} | next=({self.next_station.x},{self.next_station.y}) | route_length={len(self.assigned_route.stations)}")
        
        # SAFETY: Verify next_station is not None (DOUBLE CHECK)
        if self.next_station is None:
            print(f"💀 [{self.vehicle_id}] CRITICAL: next_station became None after route update!")
            self.next_station = self.assigned_route.stations[0]  # Emergency fallback
            print(f"🚨 [{self.vehicle_id}] Emergency fallback: Reset to first station")
        
        # TRIPLE CHECK: Ensure next_station has valid coordinates
        if not hasattr(self.next_station, 'x') or not hasattr(self.next_station, 'y'):
            print(f"💀 [{self.vehicle_id}] CRITICAL: next_station has invalid structure!")
            self.next_station = self.assigned_route.stations[0]
            print(f"🚨 [{self.vehicle_id}] Reset to valid first station: ({self.next_station.x}, {self.next_station.y})")
        
        # Update estimated arrival time
        distance_to_next = self.current_position.distance_to(self.next_station)
        travel_time_minutes = (distance_to_next / SIMULATION_CONFIG['vehicle']['speed']) * 2
        self.estimated_arrival_time = current_time + timedelta(minutes=travel_time_minutes)
    
    async def handle_passenger_alighting(self):
        """Handle passengers leaving the vehicle"""
        passengers_to_remove = []
        for passenger in self.passengers:
            # Check if passenger destination matches current position (compare coordinates)
            if (passenger.destination.x == self.current_position.x and 
                passenger.destination.y == self.current_position.y):
                passengers_to_remove.append(passenger)
                self.passengers_served += 1
                
                # Log passenger satisfaction metric
                travel_time = (datetime.now() - passenger.boarding_time).total_seconds() / 60
                target_time = (passenger.target_arrival_time - passenger.boarding_time).total_seconds() / 60
                satisfaction = max(0, 1 - (travel_time - target_time) / target_time) if target_time > 0 else 1
                self.log_metric('passenger_satisfaction', satisfaction)
        
        if passengers_to_remove:
            for passenger in passengers_to_remove:
                self.passengers.remove(passenger)
                self.total_passengers_transported += 1  # Track for analytics
                print(f"👤 Passenger {passenger.id} alighted from {self.vehicle_id} at ({self.current_position.x},{self.current_position.y})")
            print(f"🚏 {self.vehicle_id} now carrying {len(self.passengers)}/{self.capacity} passengers")
    
    async def handle_passenger_request(self, msg):
        """Handle a passenger boarding request"""
        import json
        request_data = json.loads(msg.body)
        
        if len(self.passengers) < self.capacity:
            # Accept passenger
            passenger = PassengerInfo(
                id=request_data['passenger_id'],
                origin=Position(request_data['origin']['x'], request_data['origin']['y']),
                destination=Position(request_data['destination']['x'], request_data['destination']['y']),
                boarding_time=datetime.now(),
                target_arrival_time=datetime.fromisoformat(request_data['target_arrival_time'])
            )
            self.passengers.append(passenger)
            
            await self.send_message(
                str(msg.sender),
                {'status': 'accepted', 'vehicle_id': self.vehicle_id},
                MESSAGE_TYPES['PASSENGER_REQUEST']
            )
            print(f"✅ {self.vehicle_id} accepted passenger {passenger.id} (now carrying {len(self.passengers)}/{self.capacity})")
        else:
            # Reject passenger - vehicle full
            await self.send_message(
                str(msg.sender),
                {'status': 'rejected', 'reason': 'vehicle_full'},
                MESSAGE_TYPES['PASSENGER_REQUEST']
            )
    
    def handle_boarding_list(self, body):
        """
        STEP 3: Handle BOARDING_LIST from station.
        Station sends list of passengers to board.
        
        Args:
            body: {
                "station_id": str,
                "passengers": [{"id": str, "destination": str}, ...]
            }
        """
        try:
            import json
            if isinstance(body, str):
                body = json.loads(body)
            
            station_id = body.get("station_id")
            passengers = body.get("passengers", [])
            
            boarded_count = 0
            for p in passengers:
                pid = p["id"]
                dest = p["destination"]
                
                # Check capacity (defense)
                if self.occupancy >= self.capacity:
                    print(f"⚠️ [{self.vehicle_id}] Capacity full, cannot board {pid}")
                    break
                
                # Board passenger
                self.passengers_onboard[pid] = {"destination": dest}
                self.occupancy += 1
                boarded_count += 1
                
                # Send BOARDING_CONFIRMED to passenger (async)
                asyncio.create_task(self._send_boarding_confirmed(pid))
            
            if boarded_count > 0:
                print(f"✅ [{self.vehicle_id}] Boarded {boarded_count} passengers from {station_id} | occupancy={self.occupancy}/{self.capacity}")
        
        except Exception as e:
            print(f"❌ [{self.vehicle_id}] Error handling boarding list: {e}")
            import traceback
            traceback.print_exc()
    
    async def _send_boarding_confirmed(self, passenger_id: str):
        """Send BOARDING_CONFIRMED to passenger"""
        try:
            passenger_jid = self.city.get_passenger_jid(passenger_id)
            await self.send_message(
                passenger_jid,
                {
                    "passenger_id": passenger_id,
                    "vehicle_id": self.vehicle_id
                },
                MESSAGE_TYPES['BOARDING_CONFIRMED']
            )
        except Exception:
            # Passenger might not exist (dict-based) - not critical
            pass
            print(f"❌ {self.vehicle_id} FULL - rejected passenger (capacity: {self.capacity})")
    
    async def handle_capacity_request(self, msg):
        """Handle station requests for additional capacity"""
        import json
        request_data = json.loads(msg.body)
        
        # Use coordination protocol to announce intention
        station_id = request_data.get('station_id', str(msg.sender))
        await self.coordinator.announce_intention(self, station_id)
        
        # Simple capacity sharing logic
        available_capacity = self.capacity - len(self.passengers)
        if available_capacity > 5 and not self.is_broken:
            # Vehicle can help with demand
            await self.send_message(
                str(msg.sender),
                {
                    'vehicle_id': self.vehicle_id,
                    'available_capacity': available_capacity,
                    'estimated_arrival': self.estimated_arrival_time.isoformat(),
                    'current_position': {'x': self.current_position.x, 'y': self.current_position.y}
                },
                MESSAGE_TYPES['VEHICLE_CAPACITY']
            )
    
    async def check_vehicle_health(self):
        """Monitor vehicle health and request maintenance if needed (PASSO 1)"""
        # Random breakdown check
        if not self.is_broken and random.random() < SIMULATION_CONFIG['vehicle']['breakdown_probability']:
            # Choose random breakdown type
            breakdown_types = ['tire', 'engine', 'tow']
            breakdown_weights = [0.5, 0.4, 0.1]  # 50% tire, 40% engine, 10% tow
            self.breakdown_type = random.choices(breakdown_types, weights=breakdown_weights)[0]
            
            # PASSO 1: Set BOTH flags to ensure vehicle stops
            self.is_broken = True
            self.state = "BROKEN"
            self.breakdown_time = datetime.now()
            
            print(f"💥💥💥 {self.vehicle_id} BREAKDOWN at ({self.current_position.x},{self.current_position.y})")
            print(f"   Type: {self.breakdown_type} | Passengers onboard: {self.occupancy}/{self.capacity}")
            
            # PASSO 4: Request maintenance via ACL messages to registered crews
            maintenance_crews = self.maintenance_crews_jids
            if not maintenance_crews:
                print(f"⚠️ {self.vehicle_id} has NO maintenance crews configured!")
                return
            
            print(f"📡 {self.vehicle_id} sending BREAKDOWN_ALERT to {len(maintenance_crews)} crews...")
            
            for crew_jid in maintenance_crews:
                await self.send_message(
                    crew_jid,
                    {
                        'vehicle_id': self.vehicle_id,
                        'vehicle_jid': str(self.jid),  # PASSO 2: Include vehicle_jid for reply
                        'vehicle_type': self.vehicle_type,
                        'position': {'x': self.current_position.x, 'y': self.current_position.y},
                        'breakdown_time': self.breakdown_time.isoformat(),
                        'breakdown_type': self.breakdown_type,
                        'passengers_onboard': self.occupancy
                    },
                    MESSAGE_TYPES['BREAKDOWN_ALERT']
                )
                print(f"✉️ BREAKDOWN_ALERT sent to {crew_jid}")
        
        # Check fuel level
        if self.fuel_level < 20:
            print(f"⛽ {self.vehicle_id} needs refueling (fuel: {self.fuel_level}%)")
    
    async def handle_maintenance_completed(self, msg):
        """
        PASSO 1: Handle repair completion from maintenance crew.
        This is the ONLY place (besides breakdown detection) that changes is_broken.
        """
        import json
        body = json.loads(msg.body) if isinstance(msg.body, str) else msg.body
        
        vehicle_id = body.get('vehicle_id')
        if vehicle_id != self.vehicle_id:
            # Not for us
            return
        
        breakdown_type = body.get('breakdown_type')
        repair_time = body.get('repair_time', 0)
        response_time = body.get('response_time', 0)
        
        print(f"🎉🎉🎉 [{self.vehicle_id}] REPAIR COMPLETED!")
        print(f"   Breakdown type: {breakdown_type}")
        print(f"   Response time: {response_time:.1f}s | Repair time: {repair_time:.1f}s")
        print(f"   Passengers released: {self.occupancy}")
        
        # PASSO 1: Restore vehicle to operational state
        self.is_broken = False
        self.breakdown_type = None
        self.breakdown_time = None
        self.maintenance_requested = False
        
        # Determine next state based on location
        if self.current_station_index is not None and len(self.assigned_route.stations) > 0:
            current_pos = self.current_position
            station_pos = self.assigned_route.stations[self.current_station_index]
            
            # If at station, mark as AT_STATION, else EN_ROUTE
            if current_pos.x == station_pos.x and current_pos.y == station_pos.y:
                self.state = "AT_STATION"
            else:
                self.state = "EN_ROUTE"
        else:
            self.state = "EN_ROUTE"
        
        print(f"✅ [{self.vehicle_id}] Back to service: state={self.state}")
    
    async def handle_maintenance_ack(self, msg):
        """Handle acknowledgment from maintenance crew that they're coming"""
        import json
        body = json.loads(msg.body) if isinstance(msg.body, str) else msg.body
        crew_id = body.get('crew_id', 'unknown')
        eta = body.get('eta', 0)
        
        print(f"📞 [{self.vehicle_id}] Maintenance crew {crew_id} acknowledged (ETA: {eta:.1f}s)")
    
    async def handle_passenger_request(self, msg):
        """
        🆕 Handle passenger request for transportation
        Responds with vehicle availability and estimated arrival
        """
        import json
        body = json.loads(msg.body) if isinstance(msg.body, str) else msg.body
        
        passenger_id = body.get('passenger_id')
        request_type = body.get('request_type')
        origin = body.get('origin', {})
        destination = body.get('destination', {})
        
        print(f"📨 [{self.vehicle_id}] Received passenger request from {passenger_id} (type: {request_type})")
        
        if request_type == 'availability_check':
            # Respond with current availability
            available_capacity = self.capacity - self.occupancy
            
            # Estimate arrival time (simplified - based on current route)
            estimated_arrival = datetime.now() + timedelta(minutes=random.randint(2, 8))
            
            response = {
                'vehicle_id': self.vehicle_id,
                'vehicle_jid': str(self.jid),
                'available_capacity': available_capacity,
                'estimated_arrival': estimated_arrival.isoformat(),
                'current_occupancy': self.occupancy,
                'vehicle_type': self.vehicle_type
            }
            
            await self.send_message(
                str(msg.sender),
                response,
                MESSAGE_TYPES.get('VEHICLE_CAPACITY', 'vehicle_capacity')
            )
            
            print(f"📤 [{self.vehicle_id}] Sent availability to {passenger_id}: capacity={available_capacity}")
        
        elif request_type == 'boarding_request':
            # Handle actual boarding request
            available_capacity = self.capacity - self.occupancy
            
            if available_capacity > 0 and not self.is_broken:
                # Accept passenger
                response = {
                    'vehicle_id': self.vehicle_id,
                    'status': 'accepted',
                    'message': f'Welcome aboard {self.vehicle_type} {self.vehicle_id}'
                }
                
                # Add passenger to onboard dict
                passenger_dest = Position(destination.get('x', 0), destination.get('y', 0))
                self.passengers_onboard[passenger_id] = {
                    'destination': passenger_dest,
                    'boarding_time': datetime.now()
                }
                self.occupancy += 1
                
                print(f"✅ [{self.vehicle_id}] Accepted passenger {passenger_id} ({self.occupancy}/{self.capacity})")
            else:
                # Reject passenger
                reason = 'vehicle_full' if available_capacity <= 0 else 'vehicle_broken'
                response = {
                    'vehicle_id': self.vehicle_id,
                    'status': 'rejected',
                    'reason': reason
                }
                
                print(f"❌ [{self.vehicle_id}] Rejected passenger {passenger_id}: {reason}")
            
            await self.send_message(
                str(msg.sender),
                response,
                MESSAGE_TYPES.get('PASSENGER_RESPONSE', 'passenger_response')
            )
        """Handle acknowledgment from maintenance crew"""
        import json
        body = json.loads(msg.body) if isinstance(msg.body, str) else msg.body
        
        crew_id = body.get('crew_id', 'unknown')
        status = body.get('status', 'unknown')
        estimated_arrival = body.get('estimated_arrival', 'unknown')
        
        print(f"📨 [{self.vehicle_id}] Maintenance ACK from {crew_id}: {status} (ETA: {estimated_arrival})")
        self.maintenance_requested = True
    
    async def get_station_agents_at_position(self, position: Position) -> List[str]:
        """Get station agent JIDs at the given position"""
        # Find stations at this position from city.stations
        station_jids = []
        for i, station_pos in enumerate(self.city.stations):
            if station_pos.x == position.x and station_pos.y == position.y:
                station_jids.append(f"station{i}@local")
        return station_jids
    
    async def get_maintenance_agents(self) -> List[str]:
        """Get maintenance crew agent JIDs"""
        # Return maintenance crew JIDs set by simulation coordinator
        return getattr(self, 'maintenance_crews_jids', [])
    
    async def update_status(self):
        """Update vehicle status metrics"""
        # Calculate on-time performance
        if self.total_arrivals > 0:
            on_time_rate = self.on_time_arrivals / self.total_arrivals
            self.log_metric('on_time_performance', on_time_rate)
        
        # Calculate utilization
        utilization = len(self.passengers) / self.capacity
        self.log_metric('fleet_utilization', utilization)
        
        # Log fuel efficiency
        self.log_metric('fuel_level', self.fuel_level)
    
    # Contract Net Protocol methods
    async def can_perform_task(self, task: Dict[str, Any]) -> bool:
        """Determine if vehicle can perform the requested task"""
        if self.is_broken or self.fuel_level < 20:
            return False
        
        # Check if we have available capacity
        available_capacity = self.capacity - len(self.passengers)
        required_capacity = task.get('required_capacity', 1)
        
        if available_capacity < required_capacity:
            return False
        
        # Check if station is reachable
        station_pos = Position(task['position']['x'], task['position']['y'])
        distance = abs(station_pos.x - self.current_position.x) + abs(station_pos.y - self.current_position.y)
        
        # Don't bid if station is too far
        if distance > 20:
            return False
        
        return True
    
    async def create_proposal(self, contract_id: str, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a proposal for the CNP task"""
        if not await self.can_perform_task(task):
            return None
        
        # Calculate estimated arrival time
        station_pos = Position(task['position']['x'], task['position']['y'])
        distance = abs(station_pos.x - self.current_position.x) + abs(station_pos.y - self.current_position.y)
        
        # Estimate travel time (assuming 1 unit per 30 seconds)
        travel_time_minutes = (distance * 0.5) / self.speed_modifier
        estimated_arrival = datetime.now() + timedelta(minutes=travel_time_minutes)
        
        # Calculate available capacity
        available_capacity = self.capacity - len(self.passengers)
        
        # Calculate cost based on distance and urgency
        base_cost = distance * 2
        if task.get('urgency') == 'high':
            base_cost *= 1.5
        
        proposal = {
            'contract_id': contract_id,
            'agent_id': str(self.jid),
            'vehicle_id': self.vehicle_id,
            'vehicle_type': self.vehicle_type,
            'estimated_arrival_time': estimated_arrival.isoformat(),
            'capacity': available_capacity,
            'cost': base_cost,
            'current_position': {'x': self.current_position.x, 'y': self.current_position.y},
            'fuel_level': self.fuel_level,
            'passengers_onboard': len(self.passengers)
        }
        
        return proposal
    
    async def execute_contract(self, contract_id: str, task: Dict[str, Any]):
        """Execute the awarded contract - adjust route to go to station"""
        print(f"🚀 [{self.vehicle_id}] Executing contract {contract_id} - going to station {task['station_id']}")
        
        # Update route to include the station
        station_pos = Position(task['position']['x'], task['position']['y'])
        
        # Set as next destination (CNP diverts vehicle to requesting station)
        self.next_station = station_pos
        self.state = "EN_ROUTE"  # Ensure we're moving
        
        # Calculate estimated arrival
        distance = abs(station_pos.x - self.current_position.x) + abs(station_pos.y - self.current_position.y)
        travel_time_minutes = (distance * 0.5) / self.speed_modifier
        self.estimated_arrival_time = datetime.now() + timedelta(minutes=travel_time_minutes)
        
        # Notify station that we're coming
        await self.send_message(
            task['initiator'],
            {
                'contract_id': contract_id,
                'vehicle_id': self.vehicle_id,
                'status': 'executing',
                'estimated_arrival': self.estimated_arrival_time.isoformat(),
                'current_position': {'x': self.current_position.x, 'y': self.current_position.y}
            },
            MESSAGE_TYPES['CONTRACT_NET_INFORM']
        )
        
        print(f"✅ [{self.vehicle_id}] Route adjusted: will arrive at station {task['station_id']} in ~{travel_time_minutes:.1f} minutes")
    
    async def find_alternative_route(self):
        """Find alternative route when current route is blocked by accident/event"""
        if not self.next_station or not self.assigned_route:
            return
        
        # Find alternative station to reach
        current_idx = self.current_station_index
        target_idx = min(current_idx + 2, len(self.assigned_route.stations) - 1)
        
        if target_idx > current_idx:
            # Skip blocked station
            self.current_station_index = target_idx
            self.next_station = self.assigned_route.stations[target_idx]
            print(f"🔄 {self.vehicle_id} rerouted to station {target_idx}")
            self.route_adaptations += 1
            
            # PASSO 5: Record route adaptation
            if self.metrics_collector:
                self.metrics_collector.record_route_adaptation(self.vehicle_id)