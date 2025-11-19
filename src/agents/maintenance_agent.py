"""
Maintenance crew agents for vehicle repairs - PURE SPADE
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

class MaintenanceAgent(BaseTransportAgent):
    """Agent representing a maintenance crew"""
    
    def __init__(self, jid: str, password: str, crew_id: str, city, event_manager=None, metrics_collector=None):
        super().__init__(jid, password, "maintenance_crew", metrics_collector=metrics_collector)
        
        self.crew_id = crew_id
        self.city = city
        self.event_manager = event_manager  # For traffic/environment influence
        
        # Crew state
        self.current_position = Position(
            random.randint(0, city.grid_size[0] - 1),
            random.randint(0, city.grid_size[1] - 1)
        )
        self.position = self.current_position  # Alias for dashboard compatibility
        self.is_busy = False
        self.current_job = None
        self.available_tools = ['basic_repair', 'engine_repair', 'electrical_repair']
        
        # TOW system and base management
        self.towing_vehicle = False  # True when towing a vehicle to base
        self.base_position = None  # Will be set by base_manager
        self.base_manager = None  # Will be set externally
        self.allocated_resources = {'tools': 0, 'tow_hooks': 0}  # Track allocated resources
        
        # PASSO 4: Explicit state for state machine (lowercase!)
        self.state = 'idle'  # 'idle', 'en_route', 'repairing', 'returning_to_base'
        
        # Tick counter
        self.current_tick = 0
        
        # PASSO 2: Don't touch vehicle objects directly - remove this reference
        # self.target_vehicle_agent = None  # REMOVED - use vehicle_jid instead
        
        # Job queue and prioritization (PASSO 2: structured format)
        self.job_queue = []  # List of job dicts with vehicle_jid
        self.completed_jobs = []
        
        # 🤝 COORDENAÇÃO ENTRE EQUIPAS (PASSO 3)
        self.claimed_vehicles = set()  # Veículos que esta equipa já reivindicou
        self.maintenance_crews = []  # Referências às outras equipas (será preenchido externamente)
        self.maintenance_crews_ids = []  # IDs for coordination
        
        # Performance tracking
        self.total_repairs = 0
        self.total_response_time = 0
        self.total_repair_time = 0
        
        # Timing for state machine (PASSO 2)
        self.travel_start_time = None
        self.repair_start_time = None
        
        # PASSO 6: Event manager for traffic/environment
        self.event_manager = None  # Will be set externally
        
    async def setup(self):
        """Setup maintenance-specific behaviours"""
        await super().setup()
        
        # Add unified behaviour for maintenance operations
        self.add_behaviour(self.MaintenanceMainBehaviour())
    
    async def handle_message(self, msg: Message):
        """
        PURE SPADE message handler - routes incoming messages to appropriate handlers
        """
        await super().handle_message(msg)  # Log message
        
        msg_type = msg.metadata.get('type') if msg.metadata else None
        
        try:
            if msg_type == MESSAGE_TYPES['BREAKDOWN_ALERT']:
                await self.handle_breakdown_alert(msg)
            elif msg_type == MESSAGE_TYPES['MAINTENANCE_COMPLETED']:
                # Just log - no action needed
                pass
            else:
                print(f"⚠️ [{self.crew_id}] Unknown message type: {msg_type}")
        
        except Exception as e:
            print(f"❌ [{self.crew_id}] Error handling message: {e}")
            import traceback
            traceback.print_exc()
    
    # ========================================
    # TICK-BASED STATE UPDATE (PASSO 2: State machine)
    # ========================================
    
    def update_state(self):
        """
        PASSO 2: State machine for maintenance crew (message-based only).
        States: IDLE -> TRAVELLING -> REPAIRING -> IDLE
        """
        self.current_tick += 1
        
        # 🔍 DEBUG: Log state periodically
        if self.current_tick % 50 == 0:
            print(f"🔍 [{self.crew_id}] Tick {self.current_tick}: state={self.state}, busy={self.is_busy}, "
                  f"current_job={self.current_job.get('vehicle_id') if self.current_job else None}, "
                  f"queue={len(self.job_queue)}")
        
        # State machine
        if self.state == "idle":
            # Pick next job from queue
            if not self.current_job and self.job_queue:
                self.prioritize_jobs()  # Sort by priority
                self.current_job = self.job_queue.pop(0)
                self.state = "en_route"
                self.travel_start_time = datetime.now()
                self.is_busy = True
                
                job_pos = self.current_job['position']
                distance = self.current_position.distance_to(job_pos)
                print(f"🚑 [{self.crew_id}] Starting job for {self.current_job['vehicle_id']}")
                print(f"   Breakdown: {self.current_job['breakdown_type']} | Distance: {distance:.1f}")
        
        elif self.state == "en_route":
            # PASSO 6: Consider traffic when traveling
            target_pos = self.current_job['position']
            distance = self.current_position.distance_to(target_pos)
            
            if distance < 0.5:  # Arrived
                self.current_position = target_pos
                self.state = "repairing"
                self.repair_start_time = datetime.now()
                print(f"🔧 [{self.crew_id}] ARRIVED at {self.current_job['vehicle_id']}, starting repair")
            else:
                # PASSO 6: Apply traffic modifier to movement speed
                base_step = 0.5  # Grid units per tick
                
                if self.event_manager:
                    pos = (int(self.current_position.x), int(self.current_position.y))
                    traffic_modifier = self.event_manager.get_traffic_modifier(pos)
                    step = base_step * traffic_modifier  # Slower in traffic
                else:
                    step = base_step
                
                # Move towards target
                dx = target_pos.x - self.current_position.x
                dy = target_pos.y - self.current_position.y
                
                if abs(dx) > abs(dy):
                    self.current_position.x += step if dx > 0 else -step
                else:
                    self.current_position.y += step if dy > 0 else -step
                
                self.position = self.current_position  # Update alias
        
        elif self.state == "repairing":
            # Check if repair time elapsed
            elapsed = (datetime.now() - self.repair_start_time).total_seconds()
            required_time = self.current_job.get('estimated_repair_time', 5)
            
            if elapsed >= required_time:
                # Finish job and send MAINTENANCE_COMPLETED
                asyncio.create_task(self.finish_current_job())
        
        elif self.state == "returning_to_base":
            # Travel back to base
            if not self.base_position:
                self.state = "idle"
                return
            
            distance = self.current_position.distance_to(self.base_position)
            
            if distance < 0.5:  # Arrived at base
                self.current_position = self.base_position
                self.position = self.current_position
                self.state = "idle"
                self.is_busy = False
                print(f"🏠 [{self.crew_id}] Returned to base, ready for next job")
            else:
                # Move towards base
                step = 0.5
                dx = self.base_position.x - self.current_position.x
                dy = self.base_position.y - self.current_position.y
                
                if abs(dx) > abs(dy):
                    self.current_position.x += step if dx > 0 else -step
                else:
                    self.current_position.y += step if dy > 0 else -step
                
                self.position = self.current_position
    
    # ========================================
    # PASSO 6: UNIFIED TICK-BASED BEHAVIOUR
    # ========================================
    
    class MaintenanceMainBehaviour(CyclicBehaviour):
        """PURE SPADE: Unified tick-based behaviour for maintenance crew"""
        
        async def run(self):
            """Main loop: update_state + sleep (messages received automatically)"""
            tick_rate = SIMULATION_CONFIG['simulation']['time_step']
            
            while True:
                try:
                    # STEP 1: Update internal state (state machine)
                    self.agent.update_state()
                    
                    # STEP 3: Small pause for simulation rhythm
                    await asyncio.sleep(tick_rate)
                
                except Exception as e:
                    print(f"❌ [{self.agent.crew_id}] MaintenanceMainBehaviour error: {e}")
                    import traceback
                    traceback.print_exc()
                    await asyncio.sleep(1)
    
    # ========================================
    # BREAKDOWN HANDLING
    # ========================================
    
    async def handle_breakdown_alert(self, msg):
        """
        PASSO 2: Handle breakdown alert (message-based only, no agents_registry).
        PASSO 3: Coordinate with other crews to avoid duplication.
        """
        import json
        breakdown_data = json.loads(msg.body) if isinstance(msg.body, str) else msg.body
        
        vehicle_id = breakdown_data['vehicle_id']
        vehicle_jid = breakdown_data.get('vehicle_jid', str(msg.sender))  # PASSO 2
        vehicle_position = Position(
            breakdown_data['position']['x'],
            breakdown_data['position']['y']
        )
        breakdown_time = datetime.fromisoformat(breakdown_data['breakdown_time'])
        breakdown_type = breakdown_data.get('breakdown_type', 'tire')
        passengers_onboard = breakdown_data.get('passengers_onboard', 0)
        
        print(f"📨 [{self.crew_id}] Breakdown alert: {vehicle_id} at ({vehicle_position.x},{vehicle_position.y})")
        print(f"   Type: {breakdown_type} | Passengers: {passengers_onboard}")
        
        # Check if already handling this vehicle
        if self.current_job and self.current_job.get('vehicle_id') == vehicle_id:
            print(f"⚠️ {self.crew_id} already handling {vehicle_id} - ignoring")
            return
        
        # Check if in queue
        if any(job.get('vehicle_id') == vehicle_id for job in self.job_queue):
            print(f"⚠️ {self.crew_id} already has {vehicle_id} in queue - ignoring")
            return
        
        # Determine repair time
        repair_time_key = f'repair_time_{breakdown_type}'
        estimated_repair_time = SIMULATION_CONFIG['maintenance'].get(repair_time_key, 5)
        
        # Calculate priority and distance
        priority = self.calculate_job_priority(vehicle_position, breakdown_time)
        my_distance = self.current_position.distance_to(vehicle_position)
        
        # COORDENAÇÃO ENTRE EQUIPAS: Só 1 equipa responde por breakdown
        # Verifica se outra equipa já está a tratar ou tem na queue
        for other_crew in self.maintenance_crews:
            if other_crew.crew_id == self.crew_id:
                continue
            
            # Já está a trabalhar neste veículo
            if other_crew.current_job and other_crew.current_job.get('vehicle_id') == vehicle_id:
                print(f"🚫 [{self.crew_id}] {other_crew.crew_id} já está a reparar {vehicle_id} - IGNORANDO")
                return
            
            # Já tem na queue
            if any(job.get('vehicle_id') == vehicle_id for job in other_crew.job_queue):
                print(f"🚫 [{self.crew_id}] {other_crew.crew_id} já tem {vehicle_id} na fila - IGNORANDO")
                return
        
        # SIMPLIFIED: Se não estou ocupado, aceito SEMPRE
        # Se estou ocupado, adiciono à queue
        if not self.is_busy and not self.current_job:
            print(f"✅ [{self.crew_id}] LIVRE - aceitando job imediatamente")
        else:
            print(f"⏳ [{self.crew_id}] OCUPADO - adicionando à queue")
        
        # ACCEPT job
        self.claimed_vehicles.add(vehicle_id)
        
        # PASSO 2: Create job with vehicle_jid (NOT vehicle_agent reference)
        repair_job = {
            'job_id': f"repair_{vehicle_id}_{datetime.now().timestamp()}",
            'vehicle_id': vehicle_id,
            'vehicle_jid': vehicle_jid,  # CRITICAL for sending reply
            'vehicle_type': breakdown_data.get('vehicle_type', 'bus'),
            'breakdown_type': breakdown_type,
            'position': vehicle_position,
            'breakdown_time': breakdown_time,
            'priority': priority,
            'estimated_repair_time': estimated_repair_time,
            'passengers_onboard': passengers_onboard,
            'distance': my_distance
        }
        
        self.job_queue.append(repair_job)
        self.prioritize_jobs()  # Sort by priority
        
        print(f"✅ [{self.crew_id}] ACCEPTED {vehicle_id} (Type: {breakdown_type}, Dist: {my_distance:.1f}, Est: {estimated_repair_time}s)")
        print(f"📋 [{self.crew_id}] Queue: {len(self.job_queue)} jobs")
        
        # Send acknowledgment
        await self.send_message(
            vehicle_jid,  # PASSO 2: Use vehicle_jid from message
            {
                'crew_id': self.crew_id,
                'status': 'acknowledged',
                'estimated_arrival': self.estimate_arrival_time(vehicle_position).isoformat()
            },
            MESSAGE_TYPES['MAINTENANCE_REQUEST']
        )
        print(f"✅ [{self.crew_id}] sent ACK to {vehicle_jid}")
    
    async def finish_current_job(self):
        """
        PASSO 2: Finish repair job and send MAINTENANCE_COMPLETED (message-based only).
        Does NOT touch vehicle_agent directly - sends message instead.
        """
        if not self.current_job:
            return
        
        job = self.current_job
        vehicle_jid = job['vehicle_jid']  # PASSO 2: Use stored JID
        
        # Calculate metrics
        now = datetime.now()
        response_time = (self.repair_start_time - job['breakdown_time']).total_seconds()
        repair_time = (now - self.repair_start_time).total_seconds()
        
        # Update crew metrics
        self.total_repairs += 1
        self.total_response_time += response_time
        self.total_repair_time += repair_time
        
        print(f"🎉 [{self.crew_id}] REPAIR COMPLETE: {job['vehicle_id']}")
        print(f"   Response: {response_time:.1f}s | Repair: {repair_time:.1f}s")
        
        # PASSO 5: Record breakdown response metrics
        if self.metrics_collector:
            self.metrics_collector.record_breakdown_response_time(
                job['vehicle_id'], 
                self.crew_id, 
                response_time, 
                repair_time
            )
        
        # PASSO 2: Send MAINTENANCE_COMPLETED to vehicle (NO direct object access!)
        await self.send_message(
            vehicle_jid,
            {
                'vehicle_id': job['vehicle_id'],
                'breakdown_type': job['breakdown_type'],
                'response_time': response_time,
                'repair_time': repair_time,
                'crew_id': self.crew_id
            },
            MESSAGE_TYPES['MAINTENANCE_COMPLETED']
        )
        print(f"📧 [{self.crew_id}] sent MAINTENANCE_COMPLETED to {vehicle_jid}")
        
        # Clean up
        self.claimed_vehicles.discard(job['vehicle_id'])
        self.current_job = None
        self.is_busy = False
        self.travel_start_time = None
        self.repair_start_time = None
        
        # Add to completed jobs
        self.completed_jobs.append(job)
        
        # VOLTAR À BASE
        if self.base_position:
            self.state = "returning_to_base"
            print(f"🏠 [{self.crew_id}] Voltando para base em ({self.base_position.x},{self.base_position.y})")
        else:
            self.state = "idle"
            self.is_busy = False
    
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
    
    def prioritize_jobs(self):
        """Sort job queue by priority (PASSO 2)"""
        self.job_queue.sort(key=lambda job: job['priority'], reverse=True)
    
    async def start_next_repair(self):
        """Start the next repair job in the queue"""
        if not self.job_queue:
            return
        
        # Clear previous towing state before taking new job
        self.towing_vehicle = False
        
        self.current_job = self.job_queue.pop(0)
        self.is_busy = True
        self.state = 'en_route'
        
        # Check breakdown type for TOW
        breakdown_type = self.current_job.get('breakdown_type', 'engine')
        vehicle_id = self.current_job['vehicle_id']
        print(f"🚗 Maintenance crew {self.crew_id} deployed for {vehicle_id} ({breakdown_type})")
        
        # Calculate actual response time
        response_time = (datetime.now() - self.current_job['breakdown_time']).total_seconds() / 60
        self.total_response_time += response_time
        
        # Don't start repair timer yet - wait until we reach the vehicle
        self.current_job['dispatch_time'] = datetime.now()
    
    async def continue_repair(self):
        """DEPRECATED - Use update_state() instead"""
        # This method is kept for backward compatibility but does nothing
        # All state management is now in update_state()
        pass
    
    async def _old_continue_repair(self):
        """OLD continue repair logic - DISABLED"""
        if not self.current_job:
            # No job, return to base if not there
            if self.state != 'at_base' and self.base_position:
                await self.return_to_base()
            return
        
        breakdown_type = self.current_job.get('breakdown_type', 'engine')
        target_pos = self.current_job['position']
        
        # State machine for repair process - handled in update_state() above
    
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
        
        # Update alias for dashboard
        self.position = self.current_position
    
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