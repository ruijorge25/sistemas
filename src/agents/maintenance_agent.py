"""
Maintenance crew agents for vehicle repairs
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .base_agent import BaseTransportAgent
from ..environment.city import Position
from ..config.settings import MESSAGE_TYPES, SIMULATION_CONFIG
from ..protocols.message_bus import message_bus

class MaintenanceAgent(BaseTransportAgent):
    """Agent representing a maintenance crew"""
    
    def __init__(self, jid: str, password: str, crew_id: str, city, agents_registry=None):
        super().__init__(jid, password, "maintenance_crew")
        
        self.crew_id = crew_id
        self.city = city
        self.agents_registry = agents_registry or {}  # Reference to all agents
        
        # Crew state
        self.current_position = Position(
            random.randint(0, city.grid_size[0] - 1),
            random.randint(0, city.grid_size[1] - 1)
        )
        self.is_busy = False
        self.current_job = None
        self.available_tools = ['basic_repair', 'engine_repair', 'electrical_repair']
        
        # TOW system and base management
        self.towing_vehicle = False  # True when towing a vehicle to base
        self.base_position = None  # Will be set by base_manager
        self.base_manager = None  # Will be set externally
        self.allocated_resources = {'tools': 0, 'tow_hooks': 0}  # Track allocated resources
        self.state = 'at_base'  # 'at_base', 'moving_to_vehicle', 'repairing', 'towing', 'returning_to_base'
        self.target_vehicle_agent = None  # Reference to vehicle being repaired
        
        # Job queue and prioritization
        self.job_queue = []  # List of repair requests
        self.completed_jobs = []
        
        # Performance tracking
        self.total_repairs = 0
        self.total_response_time = 0
        self.total_repair_time = 0
        
    async def setup(self):
        """Setup maintenance-specific behaviours"""
        await super().setup()
        
        # Add maintenance-specific behaviours
        self.add_behaviour(self.BreakdownResponseBehaviour())
        self.add_behaviour(self.RepairExecution())
        self.add_behaviour(self.JobPrioritization())
        
    class BreakdownResponseBehaviour(BaseTransportAgent.MessageReceiver):
        """Handle breakdown alerts from vehicles"""
        
        async def run(self):
            while True:
                # Use local message bus
                msg = await message_bus.receive_message(str(self.agent.jid), timeout=1)
                if msg:
                    msg_type = msg.get_metadata("type")
                    if msg_type == MESSAGE_TYPES['BREAKDOWN_ALERT']:
                        print(f"📨 {self.agent.crew_id} received BREAKDOWN_ALERT from {msg.sender}")
                        await self.agent.handle_breakdown_alert(msg)
                    else:
                        print(f"📬 {self.agent.crew_id} received message type: {msg_type}")
                await asyncio.sleep(0.1)  # Small delay to avoid busy-waiting
    
    class RepairExecution(BaseTransportAgent.MessageReceiver):
        """Execute repair jobs"""
        
        async def run(self):
            while True:
                if not self.agent.is_busy and self.agent.job_queue:
                    await self.agent.start_next_repair()
                elif self.agent.is_busy and self.agent.current_job:
                    await self.agent.continue_repair()
                await asyncio.sleep(1)  # Check every second
    
    class JobPrioritization(BaseTransportAgent.MessageReceiver):
        """Prioritize and manage repair jobs"""
        
        async def run(self):
            while True:
                await asyncio.sleep(10)  # Review priorities every 10 seconds
                await self.agent.prioritize_jobs()
    
    async def handle_breakdown_alert(self, msg):
        """Handle a vehicle breakdown alert"""
        import json
        breakdown_data = json.loads(msg.body)
        
        vehicle_id = breakdown_data['vehicle_id']
        vehicle_position = Position(
            breakdown_data['position']['x'],
            breakdown_data['position']['y']
        )
        breakdown_time = datetime.fromisoformat(breakdown_data['breakdown_time'])
        breakdown_type = breakdown_data.get('breakdown_type', 'tire')
        
        # Determine repair time based on breakdown type
        repair_time_key = f'repair_time_{breakdown_type}'
        estimated_repair_time = SIMULATION_CONFIG['maintenance'].get(repair_time_key, 5)
        
        # Create repair job
        repair_job = {
            'job_id': f"repair_{vehicle_id}_{datetime.now().timestamp()}",
            'vehicle_id': vehicle_id,
            'vehicle_type': breakdown_data.get('vehicle_type', 'bus'),
            'breakdown_type': breakdown_type,
            'position': vehicle_position,
            'breakdown_time': breakdown_time,
            'priority': self.calculate_job_priority(vehicle_position, breakdown_time),
            'estimated_repair_time': estimated_repair_time,
            'requester': str(msg.sender)
        }
        
        self.job_queue.append(repair_job)
        self.job_queue.sort(key=lambda job: job['priority'], reverse=True)
        
        print(f"🔧 {self.crew_id} received breakdown alert for {vehicle_id} (Type: {breakdown_type}, Est. time: {estimated_repair_time}s)")
        print(f"📋 {self.crew_id} job queue now has {len(self.job_queue)} jobs")
        
        # Send acknowledgment to vehicle
        await self.send_message(
            str(msg.sender),
            {
                'crew_id': self.crew_id,
                'status': 'acknowledged',
                'estimated_arrival': self.estimate_arrival_time(vehicle_position).isoformat()
            },
            MESSAGE_TYPES['MAINTENANCE_REQUEST']
        )
        print(f"✅ {self.crew_id} sent acknowledgment to {msg.sender}")
    
    def calculate_job_priority(self, vehicle_position: Position, breakdown_time: datetime) -> float:
        """Calculate priority for a repair job"""
        # Factors: urgency (time since breakdown), distance, passenger impact
        
        # Time urgency (higher priority for longer breakdowns)
        time_since_breakdown = (datetime.now() - breakdown_time).total_seconds() / 60  # minutes
        time_priority = min(1.0, time_since_breakdown / 30)  # Max priority after 30 minutes
        
        # Distance priority (closer vehicles get higher priority)
        distance = self.current_position.distance_to(vehicle_position)
        max_distance = (self.city.grid_size[0] + self.city.grid_size[1]) / 2
        distance_priority = 1.0 - (distance / max_distance)
        
        # Station proximity priority (vehicles near stations get higher priority)
        nearest_station_distance = min(
            vehicle_position.distance_to(station) for station in self.city.stations
        )
        station_priority = 1.0 - min(1.0, nearest_station_distance / 5.0)
        
        # Combined priority (weighted average)
        priority = (time_priority * 0.4 + distance_priority * 0.4 + station_priority * 0.2)
        
        return priority
    
    def estimate_arrival_time(self, target_position: Position) -> datetime:
        """Estimate arrival time at target position"""
        distance = self.current_position.distance_to(target_position)
        travel_time_minutes = distance * 2  # Assume 2 minutes per grid unit
        response_time = SIMULATION_CONFIG['maintenance']['response_time']
        
        return datetime.now() + timedelta(minutes=travel_time_minutes + response_time)
    
    async def start_next_repair(self):
        """Start the next repair job in the queue"""
        if not self.job_queue:
            return
        
        self.current_job = self.job_queue.pop(0)
        self.is_busy = True
        self.state = 'moving_to_vehicle'
        
        # Get reference to vehicle agent
        vehicle_id = self.current_job['vehicle_id']
        if self.agents_registry and vehicle_id in self.agents_registry:
            self.target_vehicle_agent = self.agents_registry[vehicle_id]
            print(f"🔗 {self.crew_id} locked onto {vehicle_id} agent")
        else:
            print(f"⚠️ {self.crew_id} could not find {vehicle_id} in registry")
        
        # Check breakdown type for TOW
        breakdown_type = self.current_job.get('breakdown_type', 'engine')
        print(f"🚗 Maintenance crew {self.crew_id} deployed for {self.current_job['vehicle_id']} ({breakdown_type})")
        
        # Calculate actual response time
        response_time = (datetime.now() - self.current_job['breakdown_time']).total_seconds() / 60
        self.total_response_time += response_time
        
        # Don't start repair timer yet - wait until we reach the vehicle
        self.current_job['dispatch_time'] = datetime.now()
    
    async def continue_repair(self):
        """Continue current repair job with state machine"""
        if not self.current_job:
            # No job, return to base if not there
            if self.state != 'at_base' and self.base_position:
                await self.return_to_base()
            return
        
        breakdown_type = self.current_job.get('breakdown_type', 'engine')
        target_pos = self.current_job['position']
        
        # State machine for repair process
        if self.state == 'moving_to_vehicle':
            # Move towards broken vehicle
            if self.current_position.x == target_pos.x and self.current_position.y == target_pos.y:
                # Reached vehicle
                if breakdown_type == 'tow':
                    self.towing_vehicle = True
                    self.state = 'towing'
                    print(f"🚛 {self.crew_id} started towing {self.current_job['vehicle_id']}")
                else:
                    self.state = 'repairing'
                    self.current_job['repair_start_time'] = datetime.now()
                    self.current_job['repair_end_time'] = datetime.now() + timedelta(minutes=self.current_job['estimated_repair_time'])
            else:
                # Keep moving towards vehicle
                await self.move_towards(target_pos)
        
        elif self.state == 'towing':
            # Towing vehicle back to base
            if self.base_position and (self.current_position.x != self.base_position.x or self.current_position.y != self.base_position.y):
                # Move vehicle with us
                if self.target_vehicle_agent:
                    self.target_vehicle_agent.current_position = self.current_position
                await self.move_towards(self.base_position)
            else:
                # Reached base, repair at base
                self.state = 'repairing'
                self.current_job['repair_start_time'] = datetime.now()
                self.current_job['repair_end_time'] = datetime.now() + timedelta(seconds=5)  # Fast repair at base
                print(f"🔧 {self.crew_id} repairing {self.current_job['vehicle_id']} at base")
        
        elif self.state == 'repairing':
            current_time = datetime.now()
            if current_time >= self.current_job['repair_end_time']:
                await self.complete_repair()
            else:
                remaining = (self.current_job['repair_end_time'] - current_time).total_seconds()
                if int(remaining) % 5 == 0:  # Log every 5 seconds
                    print(f"🔧 Repairing {self.current_job['vehicle_id']} - {remaining:.0f}s remaining")
        
        elif self.state == 'returning_to_base':
            await self.return_to_base()
    
    async def complete_repair(self):
        """Complete current repair job"""
        if not self.current_job:
            return
        
        vehicle_id = self.current_job['vehicle_id']
        requester = self.current_job.get('requester')
        breakdown_type = self.current_job.get('breakdown_type', 'engine')
        
        # Calculate repair time
        repair_time = (datetime.now() - self.current_job['repair_start_time']).total_seconds() / 60
        self.total_repair_time += repair_time
        self.total_repairs += 1
        
        # Release resources back to base_manager
        if self.base_manager and self.allocated_resources['tools'] + self.allocated_resources['tow_hooks'] > 0:
            self.base_manager.release_resources(
                self.allocated_resources['tools'],
                self.allocated_resources['tow_hooks']
            )
            print(f"✅ Resources released: {self.allocated_resources['tools']} tools, {self.allocated_resources['tow_hooks']} tow hooks")
            self.allocated_resources = {'tools': 0, 'tow_hooks': 0}
        
        # Fix vehicle
        if self.target_vehicle_agent:
            self.target_vehicle_agent.is_broken = False
            self.target_vehicle_agent.breakdown_type = None
            print(f"✅ {self.crew_id} REPAIRED {vehicle_id} - Vehicle is operational again!")
            self.target_vehicle_agent = None
        else:
            print(f"⚠️ {self.crew_id} completed job but had no vehicle reference")
        
        # Move job to completed list
        self.current_job['completion_time'] = datetime.now()
        self.current_job['actual_repair_time'] = repair_time
        self.completed_jobs.append(self.current_job)
        
        # Notify vehicle that repair is complete (if using XMPP)
        if requester:
            await self.send_message(
                requester,
                {
                    'crew_id': self.crew_id,
                    'vehicle_id': vehicle_id,
                    'status': 'repaired',
                    'repair_time': repair_time,
                    'completion_time': datetime.now().isoformat()
                },
                MESSAGE_TYPES['MAINTENANCE_REQUEST']
            )
        
        tow_msg = " and towed" if breakdown_type == 'tow' else ""
        print(f"✅ {self.crew_id} repaired{tow_msg} {vehicle_id}")
        
        # Reset towing state
        self.towing_vehicle = False
        self.current_job = None
        
        # Return to base instead of just becoming idle
        if self.base_position:
            self.state = 'returning_to_base'
            print(f"🏠 {self.crew_id} returning to base")
        else:
            self.is_busy = False
            self.state = 'at_base'
        
        # Log metrics
        self.log_metric('repair_completion', 1)
        self.log_metric('repair_time', repair_time)
    
    async def move_towards(self, target: Position):
        """Move one step towards target position"""
        dx = target.x - self.current_position.x
        dy = target.y - self.current_position.y
        
        # Move one step at a time (Manhattan distance)
        if abs(dx) > abs(dy) and dx != 0:
            self.current_position = Position(
                self.current_position.x + (1 if dx > 0 else -1),
                self.current_position.y
            )
        elif dy != 0:
            self.current_position = Position(
                self.current_position.x,
                self.current_position.y + (1 if dy > 0 else -1)
            )
    
    async def return_to_base(self):
        """Return to base after completing repair"""
        if not self.base_position:
            self.state = 'at_base'
            self.is_busy = False
            return
        
        # Check if at base
        if self.current_position.x == self.base_position.x and self.current_position.y == self.base_position.y:
            self.state = 'at_base'
            self.is_busy = False
            if self.base_manager:
                self.base_manager.park_at_base(self.crew_id, 'maintenance')
            print(f"🏠 {self.crew_id} parked at base")
            return
        
        # Move towards base
        await self.move_towards(self.base_position)
    
    async def prioritize_jobs(self):
        """Re-prioritize jobs in the queue"""
        if len(self.job_queue) <= 1:
            return
        
        # Recalculate priorities for all jobs
        for job in self.job_queue:
            job['priority'] = self.calculate_job_priority(job['position'], job['breakdown_time'])
        
        # Re-sort queue
        self.job_queue.sort(key=lambda job: job['priority'], reverse=True)
        
        if self.job_queue:
            print(f"🔄 Maintenance crew {self.crew_id} re-prioritized {len(self.job_queue)} jobs")
    
    async def update_status(self):
        """Update maintenance crew status metrics"""
        # Calculate average response time
        if self.total_repairs > 0:
            avg_response_time = self.total_response_time / self.total_repairs
            avg_repair_time = self.total_repair_time / self.total_repairs
            
            self.log_metric('average_response_time', avg_response_time)
            self.log_metric('average_repair_time', avg_repair_time)
        
        # Log current workload
        self.log_metric('pending_jobs', len(self.job_queue))
        self.log_metric('crew_utilization', 1.0 if self.is_busy else 0.0)
        
        # Check for overload
        if len(self.job_queue) > 5:
            print(f"⚠️  Maintenance crew {self.crew_id} is overloaded with {len(self.job_queue)} pending jobs")