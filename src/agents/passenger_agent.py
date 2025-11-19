"""
Passenger agents - independent SPADE agents that make travel decisions - PURE SPADE
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .base_agent import BaseTransportAgent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from ..environment.city import Position
from ..config.settings import MESSAGE_TYPES, SIMULATION_CONFIG
from ..protocols.contract_net import ContractNetInitiator

class PassengerAgent(BaseTransportAgent):
    """Agent representing an individual passenger"""
    
    def __init__(self, jid: str, password: str, passenger_id: str, 
                 origin: Position, destination: Position, city, nearby_vehicles=None):
        super().__init__(jid, password, "passenger")
        
        self.passenger_id = passenger_id
        self.origin = origin
        self.destination = destination
        self.city = city
        self.nearby_vehicles = nearby_vehicles or []  # Vehicle JIDs to negotiate with
        
        # Passenger state
        self.current_position = origin
        self.state = 'waiting'  # waiting, traveling, arrived, gave_up
        self.current_vehicle = None
        self.arrival_time = datetime.now()
        self.boarding_time = None
        self.completion_time = None
        
        # Preferences and constraints
        self.patience_time = SIMULATION_CONFIG['passenger']['patience_time']
        self.max_waiting_time = timedelta(minutes=self.patience_time)
        self.preferred_route = None
        self.available_options = []  # List of vehicle options
        
        # Decision making
        self.vehicle_proposals = {}  # vehicle_id -> proposal_info
        self.decision_deadline = None
        self.best_option = None
        
        # Performance tracking
        self.requests_sent = 0
        self.rejections_received = 0
        self.total_waiting_time = 0
        
        # Counters for periodic tasks
        self.route_discovery_counter = 0
        self.patience_check_counter = 0
        self.travel_check_counter = 0
        
        # Contract Net Protocol
        self.cnp_initiator = ContractNetInitiator(self, cfp_timeout=5)
        
    async def setup(self):
        """Setup passenger-specific behaviours"""
        await super().setup()
        
        # Add unified behaviour for passenger operations
        self.add_behaviour(self.PassengerMainBehaviour())
    
    async def handle_message(self, msg: Message):
        """
        PURE SPADE message handler - routes incoming messages to appropriate handlers
        """
        await super().handle_message(msg)  # Log message
        
        msg_type = msg.metadata.get('type') if msg.metadata else None
        
        try:
            import json
            body = json.loads(msg.body) if isinstance(msg.body, str) else msg.body
            
            if msg_type == MESSAGE_TYPES.get('VEHICLE_CAPACITY'):
                await self.handle_vehicle_response(body)
            elif msg_type == MESSAGE_TYPES.get('PASSENGER_RESPONSE'):
                await self.handle_booking_confirmation(body)
            else:
                print(f"⚠️ [passenger_{self.passenger_id}] Unknown message type: {msg_type}")
        
        except Exception as e:
            print(f"❌ [passenger_{self.passenger_id}] Error handling message: {e}")
            import traceback
            traceback.print_exc()
    
    class PassengerMainBehaviour(CyclicBehaviour):
        """
        PURE SPADE: Unified behaviour for all passenger operations
        - Messages received automatically via MessageReceiverBehaviour
        - Discover routes periodically
        - Monitor patience
        - Track travel progress
        """
        
        async def run(self):
            tick_rate = SIMULATION_CONFIG['simulation']['time_step']
            
            while True:
                try:
                    # STEP 1: Route discovery (periodic - every 25 ticks = ~5s)
                    
                    # STEP 2: Route discovery (periodic - every 25 ticks = ~5s)
                    self.agent.route_discovery_counter += 1
                    if self.agent.route_discovery_counter >= 25:
                        if self.agent.state == 'waiting' and not self.agent.vehicle_proposals:
                            await self.agent.discover_routes()
                        self.agent.route_discovery_counter = 0
                    
                    # STEP 3: Patience check (every 50 ticks = ~10s)
                    self.agent.patience_check_counter += 1
                    if self.agent.patience_check_counter >= 50:
                        await self.agent.check_patience()
                        self.agent.patience_check_counter = 0
                    
                    # STEP 4: Travel monitoring (every 25 ticks = ~5s)
                    self.agent.travel_check_counter += 1
                    if self.agent.travel_check_counter >= 25:
                        if self.agent.state == 'traveling':
                            await self.agent.check_arrival()
                        self.agent.travel_check_counter = 0
                    
                    await asyncio.sleep(tick_rate)
                    
                except Exception as e:
                    print(f"❌ [passenger_{self.agent.passenger_id}] Error: {e}")
                    import traceback
                    traceback.print_exc()
                    await asyncio.sleep(1)
    
    async def discover_routes(self):
        """Discover available vehicles and routes - ACTIVELY compare multiple options"""
        if not self.nearby_vehicles:
            print(f"⚠️ Passenger {self.passenger_id} has no vehicles to contact")
            return
        
        print(f"🔍 Passenger {self.passenger_id} discovering routes...")
        
        # Request information from all nearby vehicles
        for vehicle_jid in self.nearby_vehicles:
            await self.send_message(
                vehicle_jid,
                {
                    'passenger_id': self.passenger_id,
                    'origin': {'x': self.origin.x, 'y': self.origin.y},
                    'destination': {'x': self.destination.x, 'y': self.destination.y},
                    'request_type': 'availability_check',
                    'max_waiting_time': self.patience_time,
                    'urgency': self.calculate_urgency()
                },
                MESSAGE_TYPES['PASSENGER_REQUEST']
            )
            self.requests_sent += 1
        
        # Set decision deadline
        if not self.decision_deadline:
            self.decision_deadline = datetime.now() + timedelta(seconds=15)
            asyncio.create_task(self.make_travel_decision())
    
    def calculate_urgency(self) -> float:
        """Calculate how urgent this passenger's request is"""
        waiting_time = (datetime.now() - self.arrival_time).total_seconds() / 60
        urgency = min(1.0, waiting_time / self.patience_time)
        return urgency
    
    async def handle_vehicle_response(self, body):
        """Handle response from a vehicle"""
        import json
        if isinstance(body, str):
            response_data = json.loads(body)
        else:
            response_data = body
        
        vehicle_id = response_data.get('vehicle_id')
        available_capacity = response_data.get('available_capacity', 0)
        estimated_arrival = response_data.get('estimated_arrival')
        
        if available_capacity > 0:
            # Add to available options
            self.vehicle_proposals[vehicle_id] = {
                'vehicle_id': vehicle_id,
                'capacity': available_capacity,
                'estimated_arrival': datetime.fromisoformat(estimated_arrival) if estimated_arrival else None,
                'vehicle_jid': response_data.get('vehicle_jid', ''),
                'received_at': datetime.now()
            }
            
            print(f"👤 Passenger {self.passenger_id} received offer from {vehicle_id} (capacity: {available_capacity})")
    
    async def make_travel_decision(self):
        """Decide which vehicle to board based on collected proposals"""
        await asyncio.sleep(15)  # Wait for responses
        
        if not self.vehicle_proposals:
            print(f"😞 Passenger {self.passenger_id} received no offers - will retry")
            self.decision_deadline = None
            return
        
        print(f"🤔 Passenger {self.passenger_id} comparing {len(self.vehicle_proposals)} options:")
        
        ranked_options = []
        for vehicle_id, proposal in self.vehicle_proposals.items():
            score = self.evaluate_vehicle_option(proposal)
            ranked_options.append((vehicle_id, proposal, score))
            
            wait_time = (proposal['estimated_arrival'] - datetime.now()).total_seconds() / 60 if proposal.get('estimated_arrival') else 999
            print(f"  - {vehicle_id}: score={score:.2f}, wait={wait_time:.1f}min, capacity={proposal.get('capacity', 0)}")
        
        ranked_options.sort(key=lambda x: x[2], reverse=True)
        
        if ranked_options:
            best_vehicle_id, best_proposal, best_score = ranked_options[0]
            print(f"✅ Passenger {self.passenger_id} chose {best_vehicle_id} (score: {best_score:.2f})")
            await self.request_boarding(best_proposal)
    
    def evaluate_vehicle_option(self, proposal: Dict[str, Any]) -> float:
        """Evaluate a vehicle option and return a score"""
        score = 0.0
        
        # Factor 1: Waiting time (50% weight)
        if proposal.get('estimated_arrival'):
            arrival_time = proposal['estimated_arrival']
            wait_minutes = (arrival_time - datetime.now()).total_seconds() / 60
            
            if wait_minutes <= 2:
                score += 0.5
            elif wait_minutes <= 5:
                score += 0.3
            elif wait_minutes <= 10:
                score += 0.1
        
        # Factor 2: Vehicle capacity (20% weight)
        capacity = proposal.get('capacity', 0)
        if capacity > 20:
            score += 0.2
        elif capacity > 10:
            score += 0.15
        elif capacity > 5:
            score += 0.1
        
        # Factor 3: Response time (30% weight)
        received_at = proposal.get('received_at', datetime.now())
        response_time = (received_at - self.arrival_time).total_seconds()
        
        if response_time <= 30:
            score += 0.3
        elif response_time <= 60:
            score += 0.2
        elif response_time <= 120:
            score += 0.1
        
        return score
    
    async def request_boarding(self, vehicle_proposal: Dict[str, Any]):
        """Request to board the selected vehicle"""
        vehicle_jid = vehicle_proposal['vehicle_jid']
        
        await self.send_message(
            vehicle_jid,
            {
                'passenger_id': self.passenger_id,
                'origin': {'x': self.origin.x, 'y': self.origin.y},
                'destination': {'x': self.destination.x, 'y': self.destination.y},
                'request_type': 'boarding_request',
                'target_arrival_time': (datetime.now() + timedelta(minutes=15)).isoformat()
            },
            MESSAGE_TYPES['PASSENGER_REQUEST']
        )
        
        print(f"📤 Passenger {self.passenger_id} requesting boarding on {vehicle_proposal['vehicle_id']}")
    
    async def handle_booking_confirmation(self, body):
        """Handle boarding confirmation or rejection"""
        import json
        if isinstance(body, str):
            response_data = json.loads(body)
        else:
            response_data = body
        
        status = response_data.get('status')
        
        if status == 'accepted':
            self.state = 'traveling'
            self.current_vehicle = response_data.get('vehicle_id')
            self.boarding_time = datetime.now()
            
            waiting_time = (self.boarding_time - self.arrival_time).total_seconds() / 60
            self.total_waiting_time = waiting_time
            
            self.log_metric('waiting_time', waiting_time)
            
            print(f"🎉 Passenger {self.passenger_id} boarded {self.current_vehicle} (waited {waiting_time:.1f}min)")
            
        elif status == 'rejected':
            self.rejections_received += 1
            reason = response_data.get('reason', 'unknown')
            
            print(f"❌ Passenger {self.passenger_id} rejected: {reason}")
            
            # Try again
            if self.rejections_received < 3:
                self.vehicle_proposals = {}
                self.decision_deadline = None
    
    async def check_patience(self):
        """Check if passenger has exceeded patience time"""
        if self.state != 'waiting':
            return
        
        waiting_time = datetime.now() - self.arrival_time
        
        if waiting_time > self.max_waiting_time:
            self.state = 'gave_up'
            self.completion_time = datetime.now()
            
            print(f"😤 Passenger {self.passenger_id} gave up after {waiting_time.total_seconds()/60:.1f} minutes")
            
            self.log_metric('gave_up', 1)
            await self.stop()
    
    async def check_arrival(self):
        """Check if passenger has arrived at destination"""
        if self.state != 'traveling' or not self.boarding_time:
            return
        
        # Simulate arrival after ~10 minutes of travel
        travel_time = datetime.now() - self.boarding_time
        expected_travel = timedelta(minutes=10)
        
        if travel_time > expected_travel:
            await self.arrive_at_destination()
    
    async def arrive_at_destination(self):
        """Handle arrival at destination"""
        self.state = 'arrived'
        self.completion_time = datetime.now()
        self.current_position = self.destination
        
        total_time = (self.completion_time - self.arrival_time).total_seconds() / 60
        target_time = self.patience_time / 2
        
        satisfaction = max(0, 1 - (total_time - target_time) / target_time) if target_time > 0 else 1
        
        self.log_metric('satisfaction', satisfaction)
        self.log_metric('trip_completed', 1)
        
        print(f"🎯 Passenger {self.passenger_id} arrived! Total time: {total_time:.1f}min, Satisfaction: {satisfaction:.2f}")
        
        await self.stop()