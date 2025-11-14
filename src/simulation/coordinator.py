"""
Simulation coordinator that manages all agents and the overall simulation
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any

from ..agents.vehicle_agent import VehicleAgent
from ..agents.station_agent import StationAgent
from ..agents.passenger_agent import PassengerAgent
from ..agents.maintenance_agent import MaintenanceAgent
from ..environment.city import City, Position, Route
from ..config.settings import SIMULATION_CONFIG, XMPP_CONFIG

class SimulationCoordinator:
    """Coordinates the overall transportation simulation"""
    
    def __init__(self, city: City):
        self.city = city
        self.agents = {}
        self.vehicle_agents = {}
        self.station_agents = {}
        self.passenger_agents = {}
        self.maintenance_agents = {}
        
        self.simulation_start_time = None
        self.current_simulation_time = 0
        self.is_running = False
        
    async def start_simulation(self):
        """Start the transportation simulation"""
        print("🚀 Initializing Multi-Agent Transportation Simulation")
        
        self.simulation_start_time = datetime.now()
        self.is_running = True
        
        # Create and start all agents
        await self.create_station_agents()
        await self.create_vehicle_agents()
        await self.create_passenger_agents()
        await self.create_maintenance_agents()
        
        # Start simulation loop
        asyncio.create_task(self.simulation_loop())
        
        print("✅ All agents initialized and simulation started")
    
    async def stop_simulation(self):
        """Stop the simulation and all agents"""
        print("🛑 Stopping simulation...")
        self.is_running = False
        
        # Stop all agents
        for agent in self.agents.values():
            await agent.stop()
        
        print("✅ Simulation stopped")
    
    async def create_station_agents(self):
        """Create station agents for each station in the city"""
        print("🏪 Creating station agents...")
        
        for i, station_position in enumerate(self.city.stations):
            station_id = f"station_{i}"
            jid = f"{station_id}@{XMPP_CONFIG['domain']}"
            
            station_agent = StationAgent(
                jid=jid,
                password=XMPP_CONFIG['password'],
                station_id=station_id,
                position=station_position,
                station_type='mixed'
            )
            
            self.station_agents[station_id] = station_agent
            self.agents[jid] = station_agent
            
            await station_agent.start()
            print(f"✅ Station agent {station_id} created at position ({station_position.x}, {station_position.y})")
    
    async def create_vehicle_agents(self):
        """Create vehicle agents for buses and trams"""
        print("🚌 Creating vehicle agents...")
        
        num_vehicles = SIMULATION_CONFIG['city']['num_vehicles']
        routes = self.city.routes
        
        for i in range(num_vehicles):
            vehicle_id = f"vehicle_{i}"
            vehicle_type = 'bus' if i < num_vehicles * 0.7 else 'tram'  # 70% buses, 30% trams
            
            # Assign route
            assigned_route = routes[i % len(routes)] if routes else Route(f"route_{i}", [Position(0, 0)], vehicle_type)
            
            jid = f"{vehicle_id}@{XMPP_CONFIG['domain']}"
            
            vehicle_agent = VehicleAgent(
                jid=jid,
                password=XMPP_CONFIG['password'],
                vehicle_id=vehicle_id,
                vehicle_type=vehicle_type,
                assigned_route=assigned_route,
                city=self.city
            )
            
            self.vehicle_agents[vehicle_id] = vehicle_agent
            self.agents[jid] = vehicle_agent
            
            await vehicle_agent.start()
            print(f"✅ {vehicle_type.title()} agent {vehicle_id} created on route {assigned_route.id}")
    
    async def create_passenger_agents(self):
        """Create passenger agents (now as real SPADE agents)"""
        print("👥 Creating passenger agents...")
        
        num_passengers = SIMULATION_CONFIG['city']['num_passengers']
        
        # Create initial batch of passengers
        initial_passengers = min(10, num_passengers)  # Start with 10, more will spawn
        
        for i in range(initial_passengers):
            passenger_id = f"passenger_{i}"
            jid = f"{passenger_id}@{XMPP_CONFIG['domain']}"
            
            # Random origin and destination
            origin = self.city.stations[i % len(self.city.stations)]
            destination_options = [s for s in self.city.stations if s != origin]
            destination = destination_options[i % len(destination_options)] if destination_options else origin
            
            passenger_agent = PassengerAgent(
                jid=jid,
                password=XMPP_CONFIG['password'],
                passenger_id=passenger_id,
                origin=origin,
                destination=destination,
                city=self.city
            )
            
            self.passenger_agents[passenger_id] = passenger_agent
            self.agents[jid] = passenger_agent
            
            await passenger_agent.start()
            print(f"✅ Passenger agent {passenger_id} created")
        
        print(f"✅ {initial_passengers} passenger agents created (more will spawn dynamically)")
    
    async def create_maintenance_agents(self):
        """Create maintenance crew agents"""
        print("🔧 Creating maintenance agents...")
        
        num_crews = SIMULATION_CONFIG['city']['num_maintenance_crews']
        
        for i in range(num_crews):
            crew_id = f"maintenance_{i}"
            jid = f"{crew_id}@{XMPP_CONFIG['domain']}"
            
            # Create a simplified maintenance agent
            from ..agents.maintenance_agent import MaintenanceAgent
            maintenance_agent = MaintenanceAgent(
                jid=jid,
                password=XMPP_CONFIG['password'],
                crew_id=crew_id,
                city=self.city
            )
            
            self.maintenance_agents[crew_id] = maintenance_agent
            self.agents[jid] = maintenance_agent
            
            await maintenance_agent.start()
            print(f"✅ Maintenance crew {crew_id} created")
    
    async def simulation_loop(self):
        """Main simulation loop"""
        print("🔄 Starting simulation loop...")
        
        passenger_spawn_counter = 10  # Start after initial 10 passengers
        
        while self.is_running:
            # Update simulation time
            self.current_simulation_time += SIMULATION_CONFIG['simulation']['time_step']
            
            # Update city environment (traffic, weather, etc.)
            current_hour = datetime.now().hour
            self.city.update_traffic(current_hour)
            
            # Spawn new passengers periodically
            if int(self.current_simulation_time) % 30 == 0:  # Every 30 seconds
                await self.spawn_new_passenger(passenger_spawn_counter)
                passenger_spawn_counter += 1
            
            # Update agent registries for cross-agent communication
            await self.update_agent_registries()
            
            # Collect and log metrics
            await self.collect_metrics()
            
            # Sleep for one simulation step
            await asyncio.sleep(SIMULATION_CONFIG['simulation']['time_step'])
            
            # Check if simulation should end
            if self.current_simulation_time >= SIMULATION_CONFIG['simulation']['max_duration']:
                print("⏰ Simulation time limit reached")
                break
    
    async def spawn_new_passenger(self, passenger_number: int):
        """Spawn a new passenger agent during simulation"""
        import random
        
        if len(self.passenger_agents) >= SIMULATION_CONFIG['city']['num_passengers']:
            return  # Max passengers reached
        
        passenger_id = f"passenger_{passenger_number}"
        jid = f"{passenger_id}@{XMPP_CONFIG['domain']}"
        
        # Random origin and destination
        origin = random.choice(self.city.stations)
        destination_options = [s for s in self.city.stations if s != origin]
        destination = random.choice(destination_options) if destination_options else origin
        
        try:
            passenger_agent = PassengerAgent(
                jid=jid,
                password=XMPP_CONFIG['password'],
                passenger_id=passenger_id,
                origin=origin,
                destination=destination,
                city=self.city
            )
            
            self.passenger_agents[passenger_id] = passenger_agent
            self.agents[jid] = passenger_agent
            
            await passenger_agent.start()
            print(f"👤 New passenger {passenger_id} spawned: {origin} → {destination}")
            
        except Exception as e:
            print(f"⚠️  Failed to spawn passenger {passenger_id}: {e}")
    
    async def update_agent_registries(self):
        """Update agent registries so agents can find each other"""
        # Update station agents with nearby vehicles
        for station_id, station_agent in self.station_agents.items():
            nearby_vehicles = []
            nearby_stations = []
            
            for vehicle_id, vehicle_agent in self.vehicle_agents.items():
                distance = station_agent.position.distance_to(vehicle_agent.current_position)
                if distance <= 5.0:  # Within 5 grid units
                    nearby_vehicles.append(f"{vehicle_id}@{XMPP_CONFIG['domain']}")
            
            for other_station_id, other_station_agent in self.station_agents.items():
                if other_station_id != station_id:
                    distance = station_agent.position.distance_to(other_station_agent.position)
                    if distance <= 8.0:  # Within 8 grid units
                        nearby_stations.append(f"{other_station_id}@{XMPP_CONFIG['domain']}")
            
            # Update the agent's knowledge
            station_agent.nearby_vehicles = nearby_vehicles
            station_agent.nearby_stations = nearby_stations
        
        # Update vehicle agents with station and maintenance information
        for vehicle_id, vehicle_agent in self.vehicle_agents.items():
            station_agents_at_position = []
            maintenance_agents = []
            high_demand_stations = []
            station_demands = {}
            
            for station_id, station_agent in self.station_agents.items():
                distance = vehicle_agent.current_position.distance_to(station_agent.position)
                if distance <= 1.0:
                    station_agents_at_position.append(f"{station_id}@{XMPP_CONFIG['domain']}")
                
                # Track high demand stations
                if len(station_agent.passenger_queue) > 15:
                    high_demand_stations.append(station_agent.position)
                
                station_demands[station_agent.position] = len(station_agent.passenger_queue)
            
            for crew_id in self.maintenance_agents.keys():
                maintenance_agents.append(f"{crew_id}@{XMPP_CONFIG['domain']}")
            
            vehicle_agent.station_agents_at_position = station_agents_at_position
            vehicle_agent.maintenance_agents = maintenance_agents
            vehicle_agent.high_demand_stations = high_demand_stations
            vehicle_agent.station_demands = station_demands
        
        # Update passenger agents with nearby vehicles
        for passenger_id, passenger_agent in self.passenger_agents.items():
            if passenger_agent.state == 'waiting':
                nearby_vehicles = []
                
                for vehicle_id, vehicle_agent in self.vehicle_agents.items():
                    distance = passenger_agent.current_position.distance_to(vehicle_agent.current_position)
                    if distance <= 3.0 and not vehicle_agent.is_broken:  # Within 3 grid units and operational
                        nearby_vehicles.append(f"{vehicle_id}@{XMPP_CONFIG['domain']}")
                
                passenger_agent.nearby_vehicles = nearby_vehicles
        
        # Update stations with possible destinations
        for station_agent in self.station_agents.values():
            # All other stations are possible destinations
            station_agent.possible_destinations = [
                pos for pos in self.city.stations if pos != station_agent.position
            ]
    
    async def collect_metrics(self):
        """Collect performance metrics from all agents"""
        if int(self.current_simulation_time) % 60 == 0:  # Every minute
            total_passengers_waiting = sum(
                len(station.passenger_queue) for station in self.station_agents.values()
            )
            
            active_vehicles = sum(
                1 for vehicle in self.vehicle_agents.values() if not vehicle.is_broken
            )
            
            fleet_utilization = active_vehicles / len(self.vehicle_agents) if self.vehicle_agents else 0
            
            print(f"📊 Metrics at {self.current_simulation_time}s:")
            print(f"   - Passengers waiting: {total_passengers_waiting}")
            print(f"   - Active vehicles: {active_vehicles}/{len(self.vehicle_agents)}")
            print(f"   - Fleet utilization: {fleet_utilization:.2%}")
    
    def get_agent_by_type(self, agent_type: str) -> Dict[str, Any]:
        """Get agents by type"""
        if agent_type == 'vehicle':
            return self.vehicle_agents
        elif agent_type == 'station':
            return self.station_agents
        elif agent_type == 'maintenance':
            return self.maintenance_agents
        else:
            return {}