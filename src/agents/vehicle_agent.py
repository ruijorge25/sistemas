"""
Vehicle agents (buses and trams) for the transportation system
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .base_agent import BaseTransportAgent
from ..environment.city import Position, Route
from ..environment.route_optimizer import RouteOptimizer, DynamicRouteAdapter
from ..config.settings import MESSAGE_TYPES, SIMULATION_CONFIG
from ..ml.learning import QLearningRouter, ReinforcementLearner
from ..protocols.contract_net import ContractNetParticipant

@dataclass
class PassengerInfo:
    id: str
    origin: Position
    destination: Position
    boarding_time: datetime
    target_arrival_time: datetime

class VehicleAgent(BaseTransportAgent):
    """Agent representing a bus or tram vehicle"""
    
    def __init__(self, jid: str, password: str, vehicle_id: str, vehicle_type: str, 
                 assigned_route: Route, city):
        super().__init__(jid, password, f"{vehicle_type}_vehicle")
        
        self.vehicle_id = vehicle_id
        self.vehicle_type = vehicle_type  # 'bus' or 'tram'
        self.assigned_route = assigned_route
        self.city = city
        
        # Vehicle state
        self.current_position = assigned_route.stations[0] if assigned_route.stations else Position(0, 0)
        self.current_station_index = 0
        self.passengers = []  # List of PassengerInfo
        self.capacity = SIMULATION_CONFIG['vehicle']['capacity']
        self.fuel_level = SIMULATION_CONFIG['vehicle']['fuel_capacity']
        self.is_broken = False
        self.maintenance_requested = False
        
        # Movement and scheduling
        self.next_station = self.assigned_route.stations[1] if len(assigned_route.stations) > 1 else None
        self.estimated_arrival_time = datetime.now() + timedelta(minutes=5)
        self.speed_modifier = 1.0  # Affected by traffic
        
        # Performance tracking
        self.on_time_arrivals = 0
        self.total_arrivals = 0
        self.passengers_served = 0
        
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
        
    async def setup(self):
        """Setup vehicle-specific behaviours"""
        await super().setup()
        
        # Initialize route adapter
        self.route_adapter = DynamicRouteAdapter(self, self.route_optimizer)
        
        # Add vehicle-specific behaviours
        self.add_behaviour(self.MovementBehaviour())
        self.add_behaviour(self.PassengerManagement())
        self.add_behaviour(self.CapacityNegotiation())
        self.add_behaviour(self.MaintenanceMonitoring())
        self.add_behaviour(self.RouteAdaptation())
        self.add_behaviour(self.ContractNetHandler())
        
    class MovementBehaviour(BaseTransportAgent.MessageReceiver):
        """Handle vehicle movement along routes"""
        
        async def run(self):
            await asyncio.sleep(SIMULATION_CONFIG['simulation']['time_step'])
            
            if not self.agent.is_broken and self.agent.next_station:
                await self.agent.move_towards_next_station()
    
    class PassengerManagement(BaseTransportAgent.MessageReceiver):
        """Manage passenger boarding and alighting"""
        
        async def run(self):
            msg = await self.receive(timeout=1)
            if msg and msg.get_metadata("type") == MESSAGE_TYPES['PASSENGER_REQUEST']:
                await self.agent.handle_passenger_request(msg)
    
    class CapacityNegotiation(BaseTransportAgent.MessageReceiver):
        """Negotiate with stations about capacity and routing"""
        
        async def run(self):
            msg = await self.receive(timeout=1)
            if msg and msg.get_metadata("type") == MESSAGE_TYPES['STATION_DEMAND']:
                await self.agent.handle_capacity_request(msg)
    
    class MaintenanceMonitoring(BaseTransportAgent.MessageReceiver):
        """Monitor vehicle health and request maintenance"""
        
        async def run(self):
            await asyncio.sleep(10)  # Check every 10 seconds
            await self.agent.check_vehicle_health()
    
    class RouteAdaptation(BaseTransportAgent.MessageReceiver):
        """Dynamically adapt routes based on conditions"""
        
        async def run(self):
            await asyncio.sleep(20)  # Check every 20 seconds
            if self.agent.route_adapter and not self.agent.is_broken:
                await self.agent.route_adapter.evaluate_and_adapt()
    
    class ContractNetHandler(BaseTransportAgent.MessageReceiver):
        """Handle Contract Net Protocol messages"""
        
        async def run(self):
            msg = await self.receive(timeout=1)
            if msg:
                msg_type = msg.metadata.get('type', '')
                
                if msg_type == MESSAGE_TYPES['CONTRACT_NET_CFP']:
                    # Received Call for Proposals
                    await self.agent.cnp_participant.handle_cfp(msg)
                elif msg_type == MESSAGE_TYPES['CONTRACT_NET_ACCEPT']:
                    # Contract awarded
                    await self.agent.cnp_participant.handle_contract_result(msg)
                elif msg_type == MESSAGE_TYPES['CONTRACT_NET_REJECT']:
                    # Contract rejected
                    await self.agent.cnp_participant.handle_contract_result(msg)
    
    async def move_towards_next_station(self):
        """Move the vehicle towards its next station"""
        if not self.next_station:
            return
            
        # Consume fuel
        self.fuel_level -= SIMULATION_CONFIG['vehicle']['fuel_consumption_rate']
        
        # Check traffic conditions
        traffic_level = self.city.get_traffic_level(self.current_position)
        self.speed_modifier = max(0.3, 1.0 - traffic_level)
        
        # Calculate movement
        distance_to_next = self.current_position.distance_to(self.next_station)
        movement_speed = SIMULATION_CONFIG['vehicle']['speed'] * self.speed_modifier
        
        if distance_to_next <= movement_speed:
            # Arrived at station
            await self.arrive_at_station()
        else:
            # Move towards station
            dx = self.next_station.x - self.current_position.x
            dy = self.next_station.y - self.current_position.y
            distance = (dx**2 + dy**2)**0.5
            
            if distance > 0:
                move_x = (dx / distance) * movement_speed
                move_y = (dy / distance) * movement_speed
                
                self.current_position.x += move_x
                self.current_position.y += move_y
    
    async def arrive_at_station(self):
        """Handle arrival at a station"""
        self.current_position = self.next_station
        self.total_arrivals += 1
        
        # Check if on time
        current_time = datetime.now()
        if current_time <= self.estimated_arrival_time:
            self.on_time_arrivals += 1
        
        # Handle passenger alighting
        await self.handle_passenger_alighting()
        
        # Notify station of arrival
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
        
        # Move to next station in route
        self.current_station_index = (self.current_station_index + 1) % len(self.assigned_route.stations)
        self.next_station = self.assigned_route.stations[self.current_station_index]
        
        # Update estimated arrival time
        distance_to_next = self.current_position.distance_to(self.next_station)
        travel_time_minutes = (distance_to_next / SIMULATION_CONFIG['vehicle']['speed']) * 2
        self.estimated_arrival_time = current_time + timedelta(minutes=travel_time_minutes)
        
        print(f"🚌 {self.vehicle_id} arrived at station {self.current_position.x},{self.current_position.y}")
    
    async def handle_passenger_alighting(self):
        """Handle passengers leaving the vehicle"""
        passengers_to_remove = []
        for passenger in self.passengers:
            if passenger.destination == self.current_position:
                passengers_to_remove.append(passenger)
                self.passengers_served += 1
                
                # Log passenger satisfaction metric
                travel_time = (datetime.now() - passenger.boarding_time).total_seconds() / 60
                target_time = (passenger.target_arrival_time - passenger.boarding_time).total_seconds() / 60
                satisfaction = max(0, 1 - (travel_time - target_time) / target_time) if target_time > 0 else 1
                self.log_metric('passenger_satisfaction', satisfaction)
        
        for passenger in passengers_to_remove:
            self.passengers.remove(passenger)
            print(f"👤 Passenger {passenger.id} alighted from {self.vehicle_id}")
    
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
            print(f"✅ {self.vehicle_id} accepted passenger {passenger.id}")
        else:
            # Reject passenger - vehicle full
            await self.send_message(
                str(msg.sender),
                {'status': 'rejected', 'reason': 'vehicle_full'},
                MESSAGE_TYPES['PASSENGER_REQUEST']
            )
    
    async def handle_capacity_request(self, msg):
        """Handle station requests for additional capacity"""
        import json
        request_data = json.loads(msg.body)
        
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
        """Monitor vehicle health and request maintenance if needed"""
        # Random breakdown check
        if not self.is_broken and random.random() < SIMULATION_CONFIG['vehicle']['breakdown_probability']:
            self.is_broken = True
            print(f"💥 {self.vehicle_id} has broken down at {self.current_position.x},{self.current_position.y}")
            
            # Request maintenance
            maintenance_crews = await self.get_maintenance_agents()
            for crew in maintenance_crews:
                await self.send_message(
                    crew,
                    {
                        'vehicle_id': self.vehicle_id,
                        'vehicle_type': self.vehicle_type,
                        'position': {'x': self.current_position.x, 'y': self.current_position.y},
                        'breakdown_time': datetime.now().isoformat()
                    },
                    MESSAGE_TYPES['BREAKDOWN_ALERT']
                )
        
        # Check fuel level
        if self.fuel_level < 20:
            print(f"⛽ {self.vehicle_id} needs refueling (fuel: {self.fuel_level}%)")
    
    async def get_station_agents_at_position(self, position: Position) -> List[str]:
        """Get station agent JIDs at the given position"""
        # This would be populated by the simulation coordinator
        # For now, return empty list
        return []
    
    async def get_maintenance_agents(self) -> List[str]:
        """Get maintenance crew agent JIDs"""
        # This would be populated by the simulation coordinator
        # For now, return empty list
        return []
    
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
        """Execute the awarded contract"""
        print(f"🚀 {self.vehicle_id} executing contract {contract_id}")
        
        # Update route to include the station
        station_pos = Position(task['position']['x'], task['position']['y'])
        
        # Set as next destination
        self.next_station = station_pos
        
        # Notify station that we're coming
        await self.send_message(
            task['initiator'],
            {
                'contract_id': contract_id,
                'vehicle_id': self.vehicle_id,
                'status': 'executing',
                'estimated_arrival': self.estimated_arrival_time.isoformat()
            },
            MESSAGE_TYPES['CONTRACT_NET_INFORM']
        )
        
        print(f"✅ {self.vehicle_id} will arrive at station {task['station_id']} for contract {contract_id}")