"""
Station agents for bus stops and tram stations
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import deque

from .base_agent import BaseTransportAgent
from ..environment.city import Position
from ..config.settings import MESSAGE_TYPES, SIMULATION_CONFIG
from ..ml.learning import DemandPredictor, PatternRecognizer
from ..protocols.contract_net import ContractNetInitiator
from ..protocols.message_bus import message_bus

class StationAgent(BaseTransportAgent):
    """Agent representing a bus stop or tram station"""
    
    def __init__(self, jid: str, password: str, station_id: str, position: Position, 
                 station_type: str = 'mixed'):
        super().__init__(jid, password, "station")
        
        self.station_id = station_id
        self.position = position
        self.station_type = station_type  # 'bus', 'tram', or 'mixed'
        
        # Passenger queue management
        self.passenger_queue = deque()
        self.max_queue_size = SIMULATION_CONFIG['station']['max_queue_size']
        self.overcrowding_threshold = SIMULATION_CONFIG['station']['overcrowding_threshold']
        
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
        
    async def setup(self):
        """Setup station-specific behaviours"""
        await super().setup()
        
        # Add station-specific behaviours
        self.add_behaviour(self.PassengerArrivalSimulation())
        self.add_behaviour(self.VehicleMonitoring())
        self.add_behaviour(self.DemandForecasting())
        self.add_behaviour(self.ServiceRequestManagement())
        self.add_behaviour(self.ContractNetHandler())
        
    class PassengerArrivalSimulation(BaseTransportAgent.MessageReceiver):
        """Simulate passenger arrivals - REACTS TO CONCERTS/EVENTS"""
        
        async def run(self):
            while True:
                await asyncio.sleep(random.uniform(1, 3))  # Random arrival intervals
                
                # Check if new passengers arrive
                arrival_rate = SIMULATION_CONFIG['passenger']['arrival_rate']
                
                # Adjust for rush hour
                current_hour = datetime.now().hour
                rush_hours = SIMULATION_CONFIG['simulation']['rush_hours']
                for start_hour, end_hour in rush_hours:
                    if start_hour <= current_hour <= end_hour:
                        arrival_rate *= SIMULATION_CONFIG['passenger']['rush_hour_multiplier']
                        break
                
                # IMPROVEMENT: Check for dynamic events (concerts, surges)
                if self.agent.event_manager:
                    pos = (self.agent.position.x, self.agent.position.y)
                    self.agent.demand_modifier = self.agent.event_manager.get_demand_modifier(pos)
                    arrival_rate *= self.agent.demand_modifier
                    
                    if self.agent.demand_modifier > 2.0:
                        print(f"📈 Station {self.agent.station_id} experiencing {self.agent.demand_modifier:.1f}x demand surge!")
                
                if random.random() < arrival_rate:
                    await self.agent.add_passenger_to_queue()
    
    class VehicleMonitoring(BaseTransportAgent.MessageReceiver):
        """Monitor vehicle arrivals and capacity"""
        
        async def run(self):
            while True:
                msg = await message_bus.receive_message(str(self.agent.jid), timeout=1)
                if msg:
                    msg_type = msg.get_metadata("type")
                    if msg_type == MESSAGE_TYPES['VEHICLE_CAPACITY']:
                        await self.agent.handle_vehicle_arrival(msg)
                await asyncio.sleep(0.1)
    
    class DemandForecasting(BaseTransportAgent.MessageReceiver):
        """Forecast passenger demand and share with nearby stations"""
        
        async def run(self):
            while True:
                await asyncio.sleep(30)  # Update forecast every 30 seconds
                await self.agent.update_demand_forecast()
                await self.agent.share_demand_forecast()
    
    class ServiceRequestManagement(BaseTransportAgent.MessageReceiver):
        """Manage requests for additional vehicle service"""
        
        async def run(self):
            while True:
                await asyncio.sleep(5)  # Check every 5 seconds
                await self.agent.check_service_needs()
    
    class ContractNetHandler(BaseTransportAgent.MessageReceiver):
        """Handle Contract Net Protocol messages"""
        
        async def run(self):
            while True:
                msg = await message_bus.receive_message(str(self.agent.jid), timeout=1)
                if msg:
                    msg_type = msg.metadata.get('type', '')
                    
                    if msg_type == MESSAGE_TYPES['CONTRACT_NET_PROPOSE']:
                        # Received proposal from vehicle
                        await self.agent.cnp_initiator.handle_proposal(msg)
                    elif msg_type == MESSAGE_TYPES['CONTRACT_NET_INFORM']:
                        # Contract execution completed
                        await self.agent.handle_contract_completion(msg)
                await asyncio.sleep(0.1)
    
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
    
    async def board_passengers(self, vehicle_id: str, available_capacity: int):
        """Board passengers onto an available vehicle"""
        boarded_passengers = 0
        passengers_to_remove = []
        
        # Board passengers up to vehicle capacity
        for passenger in list(self.passenger_queue):
            if boarded_passengers >= available_capacity:
                break
                
            # Check if passenger hasn't exceeded patience time
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
                
                print(f"✅ Passenger {passenger['id']} boarded {vehicle_id}")
        
        # Remove passengers who boarded or gave up
        for passenger in passengers_to_remove:
            if passenger in self.passenger_queue:
                self.passenger_queue.remove(passenger)
        
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
        # This would be populated by the simulation coordinator
        # For now, return empty list
        return []
    
    async def get_vehicle_agent(self, vehicle_id: str) -> str:
        """Get vehicle agent JID by vehicle ID"""
        # This would be maintained by the simulation coordinator
        return f"{vehicle_id}@localhost"
    
    async def get_nearby_vehicles(self) -> List[str]:
        """Get nearby vehicle agent JIDs"""
        # This would be populated by the simulation coordinator
        return []
    
    async def get_nearby_stations(self) -> List[str]:
        """Get nearby station agent JIDs"""
        # This would be populated by the simulation coordinator
        return []
    
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