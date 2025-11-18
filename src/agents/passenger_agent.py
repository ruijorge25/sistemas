"""
Passenger agents - independent SPADE agents that make travel decisions
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .base_agent import BaseTransportAgent
from ..environment.city import Position
from ..config.settings import MESSAGE_TYPES, SIMULATION_CONFIG
from ..protocols.contract_net import ContractNetInitiator

class PassengerAgent(BaseTransportAgent):
    """Agent representing an individual passenger"""
    
    def __init__(self, jid: str, password: str, passenger_id: str, 
                 origin: Position, destination: Position, city):
        super().__init__(jid, password, "passenger")
        
        self.passenger_id = passenger_id
        self.origin = origin
        self.destination = destination
        self.city = city
        self.agents_registry = None  # Filled by simulation coordinator

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
        
        # Contract Net Protocol
        self.cnp_initiator = ContractNetInitiator(self, cfp_timeout=5)
        
    async def setup(self):
        """Setup passenger-specific behaviours"""
        await super().setup()
        
        # Add passenger-specific behaviours
        self.add_behaviour(self.RouteDiscovery())
        self.add_behaviour(self.VehicleNegotiation())
        self.add_behaviour(self.PatienceMonitoring())
        self.add_behaviour(self.TravelMonitoring())
        
    class RouteDiscovery(BaseTransportAgent.MessageReceiver):
        """Discover available routes and vehicles"""
        
        async def run(self):
            while True:
                if self.agent.state == 'waiting' and not self.agent.vehicle_proposals:
                    await self.agent.discover_routes()
                await asyncio.sleep(5)  # Check every 5 seconds
    
    class VehicleNegotiation(BaseTransportAgent.MessageReceiver):
        """Negotiate with vehicles for transportation"""

        async def run(self):
            subscription = self.agent.subscribe_to_messages([
                MESSAGE_TYPES['VEHICLE_CAPACITY'],
                MESSAGE_TYPES['PASSENGER_REQUEST'],
            ])
            while True:
                msg = await subscription.get()
                if not msg:
                    continue

                msg_type = msg.get_metadata("type")
                if msg_type == MESSAGE_TYPES['VEHICLE_CAPACITY']:
                    await self.agent.handle_vehicle_response(msg)
                elif msg_type == MESSAGE_TYPES['PASSENGER_REQUEST']:
                    await self.agent.handle_booking_confirmation(msg)
    
    class PatienceMonitoring(BaseTransportAgent.MessageReceiver):
        """Monitor patience and give up if waiting too long"""
        
        async def run(self):
            while True:
                await asyncio.sleep(10)  # Check every 10 seconds
                await self.agent.check_patience()
    
    class TravelMonitoring(BaseTransportAgent.MessageReceiver):
        """Monitor travel progress"""
        
        async def run(self):
            while True:
                if self.agent.state == 'traveling':
                    await self.agent.check_arrival()
                await asyncio.sleep(5)
    
    async def discover_routes(self):
        """Discover available vehicles and routes - ACTIVELY compare multiple options"""
        # Find nearest station to origin
        origin_station = self.city.get_nearest_station(self.origin)
        
        # Get connecting routes to destination
        dest_station = self.city.get_nearest_station(self.destination)
        connecting_routes = self.city.get_route_by_stations(origin_station, dest_station)
        
        # IMPROVEMENT: Evaluate ALL possible routes, not just first
        if connecting_routes:
            route_scores = []
            for route in connecting_routes:
                score = self.evaluate_route_quality(route)
                route_scores.append((route, score))
                print(f"👤 Passenger {self.passenger_id} evaluating route {route.id}: score={score:.2f}")
            
            # Choose best route
            route_scores.sort(key=lambda x: x[1], reverse=True)
            self.preferred_route = route_scores[0][0]
            print(f"✅ Passenger {self.passenger_id} selected route: {self.preferred_route.id}")
        
        # Request information from nearby vehicles
        nearby_vehicles = await self.get_nearby_vehicles()
        
        if not nearby_vehicles:
            print(f"⚠️ Passenger {self.passenger_id} found no nearby vehicles to contact")
            return

        target_arrival = (datetime.now() + self.max_waiting_time).isoformat()

        for vehicle_jid in nearby_vehicles:
            await self.send_message(
                vehicle_jid,
                {
                    'passenger_id': self.passenger_id,
                    'origin': {'x': self.origin.x, 'y': self.origin.y},
                    'destination': {'x': self.destination.x, 'y': self.destination.y},
                    'request_type': 'availability_check',
                    'max_waiting_time': self.patience_time,
                    'urgency': self.calculate_urgency(),
                    'target_arrival_time': target_arrival
                },
                MESSAGE_TYPES['PASSENGER_REQUEST']
            )
            self.requests_sent += 1
    
    def evaluate_route_quality(self, route) -> float:
        """Evaluate quality of a route based on multiple factors"""
        score = 0.0
        
        # Factor 1: Number of stops (fewer is better)
        num_stops = len(route.stations)
        if num_stops <= 5:
            score += 0.4
        elif num_stops <= 8:
            score += 0.3
        else:
            score += 0.1
        
        # Factor 2: Route popularity (from metrics if available)
        route_efficiency = getattr(route, 'efficiency_rating', 0.5)
        score += route_efficiency * 0.3
        
        # Factor 3: Distance directness
        origin_station = self.city.get_nearest_station(self.origin)
        dest_station = self.city.get_nearest_station(self.destination)
        
        if origin_station in route.stations and dest_station in route.stations:
            # Check if route goes directly
            origin_idx = route.stations.index(origin_station)
            dest_idx = route.stations.index(dest_station)
            if dest_idx > origin_idx:  # Right direction
                score += 0.3
        
        return score
    
    def calculate_urgency(self) -> float:
        """Calculate how urgent this passenger's request is"""
        waiting_time = (datetime.now() - self.arrival_time).total_seconds() / 60
        urgency = min(1.0, waiting_time / self.patience_time)
        return urgency
    
    async def handle_vehicle_response(self, msg):
        """Handle response from a vehicle"""
        import json
        response_data = json.loads(msg.body)
        
        vehicle_id = response_data.get('vehicle_id')
        available_capacity = response_data.get('available_capacity', 0)
        estimated_arrival = response_data.get('estimated_arrival')
        
        if available_capacity > 0:
            # Add to available options
            self.vehicle_proposals[vehicle_id] = {
                'vehicle_id': vehicle_id,
                'capacity': available_capacity,
                'estimated_arrival': datetime.fromisoformat(estimated_arrival) if estimated_arrival else None,
                'vehicle_jid': str(msg.sender),
                'received_at': datetime.now()
            }
            
            print(f"👤 Passenger {self.passenger_id} received offer from {vehicle_id}")
            
            # Make decision after collecting offers
            if not self.decision_deadline:
                self.decision_deadline = datetime.now() + timedelta(seconds=10)
                asyncio.create_task(self.make_travel_decision())
    
    async def make_travel_decision(self):
        """Decide which vehicle to board based on collected proposals - ACTIVE COMPARISON"""
        # Wait for deadline or until we have enough options
        await asyncio.sleep(10)
        
        if not self.vehicle_proposals:
            print(f"😞 Passenger {self.passenger_id} received no offers - trying alternative routes")
            # IMPROVEMENT: Try alternative routes or longer wait
            await self.try_alternative_routes()
            return
        
        # IMPROVEMENT: Compare ALL proposals with detailed logging
        print(f"🤔 Passenger {self.passenger_id} comparing {len(self.vehicle_proposals)} options:")
        
        ranked_options = []
        for vehicle_id, proposal in self.vehicle_proposals.items():
            score = self.evaluate_vehicle_option(proposal)
            ranked_options.append((vehicle_id, proposal, score))
            
            # Log comparison details
            wait_time = (proposal['estimated_arrival'] - datetime.now()).total_seconds() / 60 if proposal.get('estimated_arrival') else 999
            print(f"  - {vehicle_id}: score={score:.2f}, wait={wait_time:.1f}min, capacity={proposal.get('capacity', 0)}")
        
        # Sort by score
        ranked_options.sort(key=lambda x: x[2], reverse=True)
        
        if ranked_options:
            best_vehicle_id, best_vehicle, best_score = ranked_options[0]
            print(f"✅ Passenger {self.passenger_id} chose {best_vehicle_id} (score: {best_score:.2f})")
            await self.request_boarding(best_vehicle)
        
    async def try_alternative_routes(self):
        """Try finding alternative routes when first attempt fails"""
        print(f"🔄 Passenger {self.passenger_id} searching for alternatives...")
        
        # Increase patience slightly
        self.max_waiting_time += timedelta(minutes=5)
        
        # Reset and try again
        self.vehicle_proposals = {}
        self.decision_deadline = None
        await asyncio.sleep(5)
        await self.discover_routes()
    
    def evaluate_vehicle_option(self, proposal: Dict[str, Any]) -> float:
        """Evaluate a vehicle option and return a score"""
        score = 0.0
        
        # Factor 1: Waiting time (50% weight)
        if proposal.get('estimated_arrival'):
            arrival_time = proposal['estimated_arrival']
            wait_minutes = (arrival_time - datetime.now()).total_seconds() / 60
            
            # Prefer vehicles arriving sooner
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
        
        # Prefer vehicles that responded quickly
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
        
        print(f"✅ Passenger {self.passenger_id} requesting boarding on {vehicle_proposal['vehicle_id']}")
    
    async def handle_booking_confirmation(self, msg):
        """Handle boarding confirmation or rejection"""
        import json
        response_data = json.loads(msg.body)
        
        status = response_data.get('status')
        
        if status == 'accepted':
            self.state = 'traveling'
            self.current_vehicle = response_data.get('vehicle_id')
            self.boarding_time = datetime.now()
            
            waiting_time = (self.boarding_time - self.arrival_time).total_seconds() / 60
            self.total_waiting_time = waiting_time
            
            self.log_metric('waiting_time', waiting_time)
            
            print(f"🎉 Passenger {self.passenger_id} boarded {self.current_vehicle}")
            
        elif status == 'rejected':
            self.rejections_received += 1
            reason = response_data.get('reason', 'unknown')
            
            print(f"❌ Passenger {self.passenger_id} rejected: {reason}")
            
            # Try to find another vehicle
            if self.rejections_received < 5:  # Don't give up too easily
                self.vehicle_proposals = {}
                self.decision_deadline = None
                await self.discover_routes()
    
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
            
            # Stop the agent
            await self.stop()
    
    async def check_arrival(self):
        """Check if passenger has arrived at destination"""
        if self.state != 'traveling':
            return
        
        # In a real implementation, this would check with the vehicle
        # For now, we simulate arrival based on expected travel time
        if self.boarding_time:
            travel_time = datetime.now() - self.boarding_time
            expected_travel = timedelta(minutes=10)  # Simplified
            
            if travel_time > expected_travel:
                await self.arrive_at_destination()
    
    async def arrive_at_destination(self):
        """Handle arrival at destination"""
        self.state = 'arrived'
        self.completion_time = datetime.now()
        self.current_position = self.destination
        
        # Calculate satisfaction
        total_time = (self.completion_time - self.arrival_time).total_seconds() / 60
        target_time = self.patience_time / 2  # Ideal time
        
        satisfaction = max(0, 1 - (total_time - target_time) / target_time) if target_time > 0 else 1
        
        self.log_metric('satisfaction', satisfaction)
        self.log_metric('trip_completed', 1)
        
        print(f"🎯 Passenger {self.passenger_id} arrived! Total time: {total_time:.1f}min, Satisfaction: {satisfaction:.2f}")
        
        # Stop the agent
        await self.stop()
    
    async def get_nearby_vehicles(self) -> List[str]:
        """Get nearby vehicle JIDs based on current city state"""
        if not self.agents_registry:
            return getattr(self, 'nearby_vehicles', [])

        nearby = []
        for agent_id, agent in self.agents_registry.items():
            if not agent_id.startswith('vehicle_'):
                continue

            position = getattr(agent, 'current_position', None)
            if not position:
                continue

            distance = self.current_position.distance_to(position)
            nearby.append((distance, str(agent.jid)))

        nearby.sort(key=lambda x: x[0])
        # Only consider vehicles within a reasonable walking distance
        return [jid for dist, jid in nearby if dist <= 12][:4]
    
    async def update_status(self):
        """Update passenger status metrics"""
        if self.state == 'waiting':
            current_waiting = (datetime.now() - self.arrival_time).total_seconds() / 60
            self.log_metric('current_waiting_time', current_waiting)
        
        self.log_metric('state', ['waiting', 'traveling', 'arrived', 'gave_up'].index(self.state))
        self.log_metric('requests_sent', self.requests_sent)
        self.log_metric('rejections_received', self.rejections_received)