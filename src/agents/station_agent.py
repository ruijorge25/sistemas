"""
Station agents for bus stops and tram stations - PURE SPADE
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import deque

from .base_agent import BaseTransportAgent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from ..environment.city import Position
from ..config.settings import MESSAGE_TYPES, SIMULATION_CONFIG, DEBUG
from ..ml.learning import DemandPredictor, PatternRecognizer
from ..protocols.contract_net import ContractNetInitiator

class StationAgent(BaseTransportAgent):
    """Agent representing a bus stop or tram station"""
    
    def __init__(self, jid: str, password: str, station_id: str, position: Position, 
                 station_type: str = 'mixed', city=None, initial_passengers=0, metrics_collector=None, **kwargs):
        super().__init__(jid, password, "station", metrics_collector=metrics_collector)
        # Ignore kwargs like message_bus (we use global message_bus)
        
        self.station_id = station_id
        self.position = position
        self.station_type = station_type  # 'bus', 'tram', or 'mixed'
        self.city = city  # Reference to city for getting other stations
        
        # PASSO 5: Passenger queue management with structured dict
        self.passenger_queue: list = []  # List of {"id": str, "destination": str, "arrival_time": datetime}
        self.max_queue_size = SIMULATION_CONFIG['station']['max_queue_size']
        self.overcrowding_threshold = SIMULATION_CONFIG['station']['overcrowding_threshold']
        
        # Populate initial passengers for realistic simulation
        self.initial_passengers = initial_passengers
        
        # Demand forecasting
        self.demand_history = deque(maxlen=SIMULATION_CONFIG['station']['demand_forecast_window'])
        self.current_demand = 0
        self.predicted_demand = 0
        
        # ML-based prediction
        self.demand_predictor = DemandPredictor(learning_rate=0.01, history_size=200)
        self.pattern_recognizer = PatternRecognizer()
        self.ml_predictions_enabled = True
        
        # Vehicle tracking
        self.available_vehicles = {}  # vehicle_id -> vehicle_info
        self.requested_vehicles = set()
        
        # Performance metrics
        self.total_passengers_served = 0
        self.total_waiting_time = 0
        self.service_requests_sent = 0
        self.service_requests_fulfilled = 0
        
        # Contract Net Protocol
        self.cnp_initiator = ContractNetInitiator(self, cfp_timeout=10)
        
        # Dynamic events
        self.event_manager = None  # Will be set by coordinator
        self.demand_modifier = 1.0
        
        # PassengerAgent integration (Phase 1.4)
        self.passenger_agents = {}  # JID -> PassengerAgent instance
        self.passenger_spawn_enabled = False  # Can be enabled for full agent-based modeling
    
    # ========================================
    # PASSO 7: INVARIANTS
    # ========================================
    
    def check_invariants(self):
        """PASSO 7: Verify station invariants (only when DEBUG=True)"""
        if not DEBUG:
            return
        
        # Invariant 1: No duplicate passenger IDs in queue
        seen_ids = set()
        for passenger in self.passenger_queue:
            pid = passenger.get("id")
            assert pid not in seen_ids, \
                f"[{self.station_id}] INVARIANT VIOLATION: passenger {pid} duplicated in queue"
            seen_ids.add(pid)
        
        # Invariant 2: Queue size doesn't exceed max
        assert len(self.passenger_queue) <= self.max_queue_size, \
            f"[{self.station_id}] INVARIANT VIOLATION: queue size {len(self.passenger_queue)} > max {self.max_queue_size}"
        
    async def setup(self):
        """Setup station-specific behaviours"""
        await super().setup()
        
        # Add unified behaviour for station operations
        self.add_behaviour(self.StationMainBehaviour())
    
    async def handle_message(self, msg: Message):
        """
        PURE SPADE message handler - routes incoming messages to appropriate handlers
        """
        await super().handle_message(msg)
        
        msg_type = msg.metadata.get('type') if msg.metadata else None
        
        try:
            import json
            body = json.loads(msg.body) if isinstance(msg.body, str) else msg.body
            
            if msg_type == MESSAGE_TYPES['VEHICLE_ARRIVED']:
                await self.handle_vehicle_arrived(body)
            elif msg_type == MESSAGE_TYPES['CONTRACT_NET_PROPOSAL']:
                await self.cnp_initiator.handle_proposal(msg)
            elif msg_type == MESSAGE_TYPES['CONTRACT_NET_ACCEPT']:
                await self.handle_contract_completion(msg)
            elif msg_type == MESSAGE_TYPES['STATION_DEMAND']:
                # Handle demand info from other stations (future enhancement)
                pass
            else:
                print(f"⚠️ [{self.station_id}] Unknown message type: {msg_type}")
        
        except Exception as e:
            print(f"❌ [{self.station_id}] Error handling message: {e}")
            import traceback
            traceback.print_exc()
    
    class StationMainBehaviour(CyclicBehaviour):
        """
        PURE SPADE: Unified behaviour for all station operations
        - Messages are received automatically via MessageReceiverBehaviour (base_agent)
        - Generate passengers periodically
        - Monitor demand and request vehicles if needed
        """
        
        async def run(self):
            tick_rate = SIMULATION_CONFIG['simulation']['time_step']
            passenger_gen_counter = 0
            demand_check_counter = 0
            
            while True:
                try:
                    # STEP 1: Update station state
                    self.agent.update_state()
                    
                    # STEP 2: Passenger generation (periodic)
                    passenger_gen_counter += 1
                    if passenger_gen_counter >= 10:  # Every ~2s with 0.2s tick
                        await self.agent.add_passenger_to_queue()
                        passenger_gen_counter = 0
                    
                    # STEP 3: Demand monitoring (periodic)
                    demand_check_counter += 1
                    if demand_check_counter >= 25:  # Every ~5s
                        await self.agent.check_service_needs()
                        demand_check_counter = 0
                    
                    await asyncio.sleep(tick_rate)
                    
                except Exception as e:
                    print(f"❌ [{self.agent.station_id}] StationMainBehaviour error: {e}")
                    import traceback
                    traceback.print_exc()
                    await asyncio.sleep(1)
    
    # ========================================
    # TICK-BASED STATE UPDATE
    # ========================================
    
    def update_state(self):
        """
        Update station state every tick - AUTONOMOUS BEHAVIOR
        Handles demand forecasting and service requests.
        """
        self.current_tick += 1
        
        # PASSO 7: Check invariants every 50 ticks (if DEBUG=True)
        if DEBUG and self.current_tick % 50 == 0:
            self.check_invariants()
        
        # Update demand forecast every 300 ticks (~30 seconds at 0.1s ticks)
        if self.current_tick % 300 == 0:
            self._update_demand_forecast_sync()
            asyncio.create_task(self.share_demand_forecast())
        
        # Check service needs every 50 ticks (~5 seconds)
        if self.current_tick % 50 == 0:
            asyncio.create_task(self.check_service_needs())
        
        # Remove impatient passengers every 100 ticks (~10 seconds)
        if self.current_tick % 100 == 0:
            self._remove_impatient_passengers()
    
    def _update_demand_forecast_sync(self):
        """Update demand forecast (synchronous version)"""
        queue_size = len(self.passenger_queue)
        self.current_demand = queue_size
        self.demand_history.append(queue_size)
        
        # ML prediction
        if self.ml_predictions_enabled and len(self.demand_history) > 5:
            try:
                history_list = list(self.demand_history)
                predicted = self.demand_predictor.predict_next(history_list)
                
                # Pattern recognition
                current_hour = datetime.now().hour
                pattern_boost = self.pattern_recognizer.get_demand_boost(
                    current_hour, 
                    self.position.x, 
                    self.position.y
                )
                
                self.predicted_demand = predicted * pattern_boost
            except Exception as e:
                # Fallback to simple average
                self.predicted_demand = sum(self.demand_history) / len(self.demand_history)
        else:
            # Simple average for fallback
            if len(self.demand_history) > 0:
                self.predicted_demand = sum(self.demand_history) / len(self.demand_history)
    
    def _remove_impatient_passengers(self):
        """Remove passengers who waited too long (synchronous)"""
        now = datetime.now()
        initial_size = len(self.passenger_queue)
        passengers_to_remove = []
        
        for passenger in self.passenger_queue:
            wait_time = (now - passenger['arrival_time']).total_seconds() / 60
            if wait_time > passenger['patience_time']:
                passengers_to_remove.append(passenger)
        
        for passenger in passengers_to_remove:
            self.passenger_queue.remove(passenger)
        
        if passengers_to_remove:
            print(f"⏰ Station {self.station_id}: {len(passengers_to_remove)} passengers left due to long wait")
    
    # ========================================
    # PASSENGER & VEHICLE MANAGEMENT
    # ========================================
    
    async def add_passenger_to_queue(self):
        """Add a new passenger to the station queue"""
        if len(self.passenger_queue) < self.max_queue_size:
            passenger_id = f"passenger_{self.station_id}_{len(self.passenger_queue)}_{datetime.now().timestamp()}"
            
            # Generate random destination
            destinations = await self.get_possible_destinations()
            if destinations:
                destination = random.choice(destinations)
                
                passenger_info = {
                    'id': passenger_id,
                    'arrival_time': datetime.now(),
                    'origin': self.position,
                    'destination': destination,
                    'patience_time': SIMULATION_CONFIG['passenger']['patience_time']
                }
                
                self.passenger_queue.append(passenger_info)
                self.current_demand += 1
                
                print(f"👤 New passenger {passenger_id} arrived at station {self.station_id}")
                
                # Check if we need to request additional service
                if len(self.passenger_queue) > self.overcrowding_threshold:
                    await self.request_additional_service()
        else:
            print(f"⚠️  Station {self.station_id} queue is full, passenger turned away")
    
    async def handle_vehicle_arrival(self, msg):
        """Handle a vehicle arriving at the station"""
        import json
        vehicle_data = json.loads(msg.body)
        
        vehicle_id = vehicle_data['vehicle_id']
        available_capacity = vehicle_data['available_capacity']
        
        # Update available vehicles
        self.available_vehicles[vehicle_id] = {
            'capacity': available_capacity,
            'arrival_time': datetime.now(),
            'vehicle_type': vehicle_data.get('vehicle_type', 'bus')
        }
        
        print(f"🚌 Vehicle {vehicle_id} arrived at station {self.station_id} with {available_capacity} capacity")
        
        # Board passengers
        await self.board_passengers(vehicle_id, available_capacity)
        
        # Remove vehicle from requested list if it was requested
        self.requested_vehicles.discard(vehicle_id)
    
    async def handle_vehicle_arrived(self, body):
        """
        PASSO 5: Handle VEHICLE_ARRIVED message from vehicle.
        Strict capacity control - never send more passengers than vehicle can hold.
        
        Args:
            body: {
                "vehicle_id": str,
                "station_id": str,
                "capacity": int,
                "occupancy": int,
                "position": {"x": int, "y": int}
            }
        """
        try:
            # Parse JSON if body is a string
            import json
            if isinstance(body, str):
                body = json.loads(body)
            
            vehicle_id = body["vehicle_id"]
            station_id = body["station_id"]
            capacity = body["capacity"]
            occupancy = body["occupancy"]
            
            # PASSO 5: Calculate free capacity (strict)
            free_capacity = max(0, capacity - occupancy)
            
            print(f"🚌 [{self.station_id}] Vehicle {vehicle_id} arrived | free={free_capacity}, queue={len(self.passenger_queue)}")
            
            # If no capacity or no passengers, send empty boarding list
            if free_capacity <= 0:
                print(f"⚠️ [{self.station_id}] Vehicle {vehicle_id} is FULL, no boarding")
                return
            
            if len(self.passenger_queue) == 0:
                print(f"ℹ️ [{self.station_id}] No passengers waiting")
                return
            
            # PASSO 5: Select passengers to board (FIFO, respecting capacity)
            boarding_count = min(free_capacity, len(self.passenger_queue))
            boarding_passengers = []
            
            for _ in range(boarding_count):
                if self.passenger_queue:
                    passenger = self.passenger_queue.pop(0)  # REMOVE from queue! (FIFO)
                    
                    # PASSO 5: Record passenger served with waiting time
                    if self.metrics_collector:
                        waiting_time = (datetime.now() - passenger['arrival_time']).total_seconds() / 60  # minutes
                        self.metrics_collector.record_passenger_served(self.station_id, waiting_time)
                    
                    # Convert Position to station_id if needed
                    if isinstance(passenger.get('destination'), Position):
                        dest_pos = passenger['destination']
                        dest_id = self._get_station_id_at_position(dest_pos)
                    else:
                        dest_id = passenger.get('destination')
                    
                    boarding_passengers.append({
                        "id": passenger['id'],
                        "destination": dest_id
                    })
                    
                    self.total_passengers_served += 1
            
            print(f"✅ [{self.station_id}] Boarding {len(boarding_passengers)} passengers to {vehicle_id}")
            
            # Send BOARDING_LIST to vehicle
            vehicle_jid = self.city.get_vehicle_jid(vehicle_id)
            await self.send_message(
                vehicle_jid,
                {
                    "station_id": self.station_id,
                    "passengers": boarding_passengers
                },
                MESSAGE_TYPES['BOARDING_LIST']
            )
            
        except Exception as e:
            print(f"❌ [{self.station_id}] Error handling vehicle arrival: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_station_id_at_position(self, position: Position) -> str:
        """Map Position to station_id"""
        if self.city and hasattr(self.city, 'stations'):
            for idx, station_pos in enumerate(self.city.stations):
                if station_pos.x == position.x and station_pos.y == position.y:
                    return f"station_{idx}"
        return f"station_at_{position.x}_{position.y}"

    
    async def board_passengers(self, vehicle_id: str, available_capacity: int):
        """Board passengers onto an available vehicle"""
        boarded_passengers = 0
        passengers_to_remove = []
        
        # Board passengers up to vehicle capacity
        for passenger in list(self.passenger_queue):
            if boarded_passengers >= available_capacity:
                break
                
            # Check if passenger hasn't exceeded patience time (if defined)
            if 'patience_time' in passenger:
                waiting_time = (datetime.now() - passenger['arrival_time']).total_seconds() / 60
                if waiting_time > passenger['patience_time']:
                    # Passenger gave up waiting
                    passengers_to_remove.append(passenger)
                    print(f"😞 Passenger {passenger['id']} gave up waiting at station {self.station_id}")
                    continue
            
            # Find vehicles that can service this passenger's destination
            vehicle_agent = await self.get_vehicle_agent(vehicle_id)
            if vehicle_agent:
                # Send passenger request to vehicle
                await self.send_message(
                    vehicle_agent,
                    {
                        'passenger_id': passenger['id'],
                        'origin': {'x': passenger['origin'].x, 'y': passenger['origin'].y},
                        'destination': {'x': passenger['destination'].x, 'y': passenger['destination'].y},
                        'target_arrival_time': (datetime.now() + timedelta(minutes=15)).isoformat()
                    },
                    MESSAGE_TYPES['PASSENGER_REQUEST']
                )
                
                passengers_to_remove.append(passenger)
                boarded_passengers += 1
                self.total_passengers_served += 1
                self.total_waiting_time += waiting_time
                
                print(f"👥 Passenger {passenger['id']} boarded {vehicle_id} at station {self.station_id}")
        
        # Remove passengers who boarded or gave up
        for passenger in passengers_to_remove:
            if passenger in self.passenger_queue:
                self.passenger_queue.remove(passenger)
        
        if boarded_passengers > 0:
            print(f"🚏 Station {self.station_id}: {boarded_passengers} passengers boarded {vehicle_id} (queue: {len(self.passenger_queue)} remaining)")
        
        self.current_demand = len(self.passenger_queue)
    
    async def request_additional_service(self):
        """Request additional vehicle service using Contract Net Protocol"""
        if len(self.requested_vehicles) > 0:
            return  # Already requested service
        
        print(f"🚨 Station {self.station_id} initiating CNP for additional service (queue: {len(self.passenger_queue)})")
        
        # Get nearby vehicles as participants
        nearby_vehicles = await self.get_nearby_vehicles()
        
        if not nearby_vehicles:
            print(f"❌ No vehicles available for CNP at station {self.station_id}")
            return
        
        # Create task description for CNP
        task_description = {
            'station_id': self.station_id,
            'position': {'x': self.position.x, 'y': self.position.y},
            'demand_level': len(self.passenger_queue),
            'urgency': 'high' if len(self.passenger_queue) > self.overcrowding_threshold * 1.5 else 'medium',
            'max_cost': 100,
            'required_capacity': min(len(self.passenger_queue), 50)
        }
        
        # Initiate Contract Net Protocol
        contract_id = await self.cnp_initiator.initiate_cfp(task_description, nearby_vehicles)
        
        if contract_id:
            self.service_requests_sent += 1
            # PASSO 5: Record CNP activation
            if self.metrics_collector:
                self.metrics_collector.record_contract_net_activation(self.station_id, len(self.passenger_queue))
            print(f"📋 CNP initiated: {contract_id} with {len(nearby_vehicles)} vehicles")
    
    async def handle_contract_completion(self, msg):
        """Handle notification of contract completion"""
        import json
        data = json.loads(msg.body)
        contract_id = data.get('contract_id')
        
        print(f"✅ Contract {contract_id} completed by {msg.sender}")
        self.service_requests_fulfilled += 1
        
        # Remove vehicle from requested set
        vehicle_id = str(msg.sender).split('@')[0]
        if vehicle_id in self.requested_vehicles:
            self.requested_vehicles.remove(vehicle_id)
    
    async def update_demand_forecast(self):
        """Update demand forecast based on historical data"""
        self.demand_history.append(self.current_demand)
        
        # Get current time info
        current_hour = datetime.now().hour
        day_of_week = datetime.now().weekday()
        
        # Add observation to ML predictor
        if self.ml_predictions_enabled:
            self.demand_predictor.add_observation(self.current_demand, current_hour, day_of_week)
            
            # Use ML prediction
            self.predicted_demand = self.demand_predictor.predict(current_hour, day_of_week)
            
            # Detect patterns
            is_rush_hour = self.pattern_recognizer.detect_rush_hour(list(self.demand_history))
            is_anomaly = self.pattern_recognizer.detect_anomaly(
                self.current_demand, 
                list(self.demand_history)
            )
            
            if is_rush_hour:
                print(f"🚨 Station {self.station_id}: Rush hour detected! Predicted demand: {self.predicted_demand:.1f}")
            
            if is_anomaly:
                print(f"⚠️  Station {self.station_id}: Unusual demand detected (current: {self.current_demand})")
        else:
            # Fallback: Simple moving average prediction
            if len(self.demand_history) >= 3:
                self.predicted_demand = sum(list(self.demand_history)[-3:]) / 3
            else:
                self.predicted_demand = self.current_demand
        
        # Log demand metrics
        self.log_metric('current_demand', self.current_demand)
        self.log_metric('predicted_demand', self.predicted_demand)
    
    async def share_demand_forecast(self):
        """Share demand forecast with nearby stations"""
        nearby_stations = await self.get_nearby_stations()
        
        for station_agent in nearby_stations:
            await self.send_message(
                station_agent,
                {
                    'station_id': self.station_id,
                    'position': {'x': self.position.x, 'y': self.position.y},
                    'current_demand': self.current_demand,
                    'predicted_demand': self.predicted_demand,
                    'queue_length': len(self.passenger_queue)
                },
                MESSAGE_TYPES['STATION_DEMAND']
            )
    
    async def check_service_needs(self):
        """Check if station needs to request service"""
        # Check queue length and waiting times
        if len(self.passenger_queue) > self.overcrowding_threshold:
            # Check if any passengers have been waiting too long
            long_waiting_passengers = 0
            for passenger in self.passenger_queue:
                waiting_time = (datetime.now() - passenger['arrival_time']).total_seconds() / 60
                if waiting_time > passenger['patience_time'] * 0.8:  # 80% of patience time
                    long_waiting_passengers += 1
            
            if long_waiting_passengers > 3:
                await self.request_additional_service()
    
    async def get_possible_destinations(self) -> List[Position]:
        """Get list of possible destinations from this station"""
        if not self.city or not self.city.stations:
            return []
        
        # Return all other stations as possible destinations
        destinations = [s for s in self.city.stations if s != self.position]
        return destinations
    
    async def get_vehicle_agent(self, vehicle_id: str) -> str:
        """Get vehicle agent JID by vehicle ID"""
        # Convert vehicle_id to proper JID format
        return f"{vehicle_id}@local"
    
    async def get_nearby_vehicles(self) -> List[str]:
        """Get nearby vehicle agent JIDs using city's vehicle registry"""
        if not hasattr(self, 'vehicle_registry') or not self.vehicle_registry:
            return []
        
        # Use city's method to find vehicles within radius
        radius = 10.0  # Search within 10 grid units
        nearby_jids = self.city.get_vehicles_within_radius(
            self.position, 
            radius, 
            self.vehicle_registry
        )
        
        return nearby_jids
    
    async def get_nearby_stations(self, radius: float = 15.0) -> List[str]:
        """Get nearby station JIDs within radius for collaboration"""
        try:
            if not hasattr(self, 'city') or self.city is None:
                return []
            
            nearby = []
            
            # Iterate through all city stations
            for idx, station_pos in enumerate(self.city.stations):
                # Calculate distance
                distance = self.position.distance_to(station_pos)
                
                # Exclude self (distance=0) and stations beyond radius
                if 0 < distance <= radius:
                    # Generate station JID (format: station_N@localhost)
                    station_jid = f"station_{idx}@localhost"
                    
                    # Don't include self
                    if station_jid != str(self.jid):
                        nearby.append((station_jid, distance))
            
            # Sort by distance
            nearby.sort(key=lambda x: x[1])
            
            return [jid for jid, dist in nearby]
            
        except Exception as e:
            # Silently handle - not critical for core functionality
            return []
    
    async def spawn_passenger_agent(self, destination_station: Position) -> Optional['PassengerAgent']:
        """
        Spawn a PassengerAgent for realistic agent-based passenger modeling (Phase 1.4).
        This enables passengers to actively negotiate and evaluate routes.
        
        Args:
            destination_station: Position of destination station
            
        Returns:
            PassengerAgent instance if spawning enabled, None otherwise
        """
        try:
            if not self.passenger_spawn_enabled:
                # Agent spawning disabled - use simple dict-based passengers
                return None
                
            from src.agents.passenger_agent import PassengerAgent
            import uuid
            
            # Create unique JID for passenger
            passenger_id = f"passenger_{uuid.uuid4().hex[:8]}"
            passenger_jid = f"{passenger_id}@localhost"
            
            # Create passenger agent
            passenger = PassengerAgent(
                jid=passenger_jid,
                password="passenger_pass",
                passenger_id=passenger_id,
                origin=self.position,
                destination=destination_station,
                city=self.city
            )
            
            # Start the agent
            await passenger.start(auto_register=True)
            self.passenger_agents[passenger_jid] = passenger
            
            self.log(f"Spawned PassengerAgent {passenger_id} going to ({destination_station.x},{destination_station.y})", "info")
            return passenger
            
        except Exception as e:
            self.log(f"Error spawning passenger agent: {e}", "error")
            import traceback
            traceback.print_exc()
            return None
    
    async def enable_passenger_agents(self, enable: bool = True):
        """
        Enable/disable PassengerAgent spawning for agent-based passenger modeling.
        When disabled (default), uses simple dict-based passengers.
        When enabled, spawns actual PassengerAgent instances.
        
        Args:
            enable: True to enable agent-based passengers, False for dict-based
        """
        self.passenger_spawn_enabled = enable
        status = "ENABLED" if enable else "DISABLED"
        self.log(f"PassengerAgent spawning {status}", "info")
    
    async def update_status(self):
        """Update station status metrics"""
        # Calculate average waiting time
        if self.total_passengers_served > 0:
            avg_waiting_time = self.total_waiting_time / self.total_passengers_served
            self.log_metric('average_waiting_time', avg_waiting_time)
        
        # Calculate service fulfillment rate
        if self.service_requests_sent > 0:
            fulfillment_rate = self.service_requests_fulfilled / self.service_requests_sent
            self.log_metric('service_fulfillment_rate', fulfillment_rate)
        
        # Log current queue status
        self.log_metric('queue_length', len(self.passenger_queue))