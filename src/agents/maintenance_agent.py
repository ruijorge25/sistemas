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

class MaintenanceAgent(BaseTransportAgent):
    """Agent representing a maintenance crew"""
    
    def __init__(self, jid: str, password: str, crew_id: str, city):
        super().__init__(jid, password, "maintenance_crew")
        
        self.crew_id = crew_id
        self.city = city
        
        # Crew state
        self.current_position = Position(
            random.randint(0, city.grid_size[0] - 1),
            random.randint(0, city.grid_size[1] - 1)
        )
        self.is_busy = False
        self.current_job = None
        self.available_tools = ['basic_repair', 'engine_repair', 'electrical_repair']
        
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
            msg = await self.receive(timeout=1)
            if msg and msg.get_metadata("type") == MESSAGE_TYPES['BREAKDOWN_ALERT']:
                await self.agent.handle_breakdown_alert(msg)
    
    class RepairExecution(BaseTransportAgent.MessageReceiver):
        """Execute repair jobs"""
        
        async def run(self):
            if not self.agent.is_busy and self.agent.job_queue:
                await self.agent.start_next_repair()
            elif self.agent.is_busy and self.agent.current_job:
                await self.agent.continue_repair()
    
    class JobPrioritization(BaseTransportAgent.MessageReceiver):
        """Prioritize and manage repair jobs"""
        
        async def run(self):
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
        
        # Create repair job
        repair_job = {
            'job_id': f"repair_{vehicle_id}_{datetime.now().timestamp()}",
            'vehicle_id': vehicle_id,
            'vehicle_type': breakdown_data.get('vehicle_type', 'bus'),
            'position': vehicle_position,
            'breakdown_time': breakdown_time,
            'priority': self.calculate_job_priority(vehicle_position, breakdown_time),
            'estimated_repair_time': SIMULATION_CONFIG['maintenance']['repair_time'],
            'requester': str(msg.sender)
        }
        
        self.job_queue.append(repair_job)
        self.job_queue.sort(key=lambda job: job['priority'], reverse=True)
        
        print(f"🔧 Maintenance crew {self.crew_id} received breakdown alert for {vehicle_id}")
        
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
        
        print(f"🚗 Maintenance crew {self.crew_id} starting repair of {self.current_job['vehicle_id']}")
        
        # Move to vehicle location (simplified - instant teleport for now)
        self.current_position = self.current_job['position']
        
        # Calculate actual response time
        response_time = (datetime.now() - self.current_job['breakdown_time']).total_seconds() / 60
        self.total_response_time += response_time
        
        # Start repair timer
        self.current_job['repair_start_time'] = datetime.now()
        self.current_job['repair_end_time'] = (
            datetime.now() + timedelta(minutes=self.current_job['estimated_repair_time'])
        )
    
    async def continue_repair(self):
        """Continue current repair job"""
        if not self.current_job:
            return
        
        current_time = datetime.now()
        
        # Check if repair is complete
        if current_time >= self.current_job['repair_end_time']:
            await self.complete_repair()
        else:
            # Repair still in progress
            remaining_time = (self.current_job['repair_end_time'] - current_time).total_seconds() / 60
            print(f"🔧 Repairing {self.current_job['vehicle_id']} - {remaining_time:.1f} minutes remaining")
    
    async def complete_repair(self):
        """Complete current repair job"""
        if not self.current_job:
            return
        
        vehicle_id = self.current_job['vehicle_id']
        requester = self.current_job['requester']
        
        # Calculate repair time
        repair_time = (datetime.now() - self.current_job['repair_start_time']).total_seconds() / 60
        self.total_repair_time += repair_time
        self.total_repairs += 1
        
        # Move job to completed list
        self.current_job['completion_time'] = datetime.now()
        self.current_job['actual_repair_time'] = repair_time
        self.completed_jobs.append(self.current_job)
        
        # Notify vehicle that repair is complete
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
        
        print(f"✅ Maintenance crew {self.crew_id} completed repair of {vehicle_id}")
        
        # Reset state
        self.current_job = None
        self.is_busy = False
        
        # Log metrics
        self.log_metric('repair_completion', 1)
        self.log_metric('repair_time', repair_time)
    
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