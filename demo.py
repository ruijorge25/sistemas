"""
Demo script that shows the system components without requiring XMPP
"""
import asyncio
import time
from src.environment.city import City, Position
from src.config.settings import SIMULATION_CONFIG
from src.visualization.console import ConsoleVisualizer

class MockAgent:
    """Mock agent for demonstration purposes"""
    def __init__(self, agent_id, position, agent_type):
        self.id = agent_id
        self.position = position
        self.agent_type = agent_type
        self.is_broken = False
        self.passenger_queue = []
        
    def update_position(self, new_position):
        self.position = new_position

class DemoSimulation:
    """Demonstration simulation without SPADE agents"""
    
    def __init__(self):
        self.city = City(SIMULATION_CONFIG['city'])
        self.visualizer = ConsoleVisualizer(self.city)
        self.vehicles = {}
        self.stations = {}
        self.simulation_time = 0
        
    def setup_demo_agents(self):
        """Create mock agents for demonstration"""
        # Create mock vehicles
        for i in range(5):
            vehicle_id = f"vehicle_{i}"
            vehicle_type = 'bus' if i < 3 else 'tram'
            start_pos = self.city.stations[i % len(self.city.stations)]
            
            vehicle = MockAgent(vehicle_id, start_pos, vehicle_type)
            vehicle.vehicle_type = vehicle_type
            vehicle.current_position = start_pos
            self.vehicles[vehicle_id] = vehicle
        
        # Create mock stations
        for i, station_pos in enumerate(self.city.stations):
            station_id = f"station_{i}"
            station = MockAgent(station_id, station_pos, 'station')
            # Simulate some passenger queues
            queue_size = (i * 3) % 8  # Varying queue sizes
            station.passenger_queue = [f"passenger_{j}" for j in range(queue_size)]
            self.stations[station_id] = station
    
    def update_simulation(self):
        """Update the simulation state"""
        self.simulation_time += 1
        
        # Move vehicles along their routes
        for vehicle in self.vehicles.values():
            if not vehicle.is_broken:
                # Simple movement: move towards random nearby station
                current_route = self.city.routes[0] if self.city.routes else None
                if current_route and current_route.stations:
                    # Find next station in route
                    current_idx = 0
                    for idx, station in enumerate(current_route.stations):
                        if station.x == vehicle.current_position.x and station.y == vehicle.current_position.y:
                            current_idx = idx
                            break
                    
                    next_idx = (current_idx + 1) % len(current_route.stations)
                    target = current_route.stations[next_idx]
                    
                    # Move towards target
                    dx = 1 if target.x > vehicle.current_position.x else (-1 if target.x < vehicle.current_position.x else 0)
                    dy = 1 if target.y > vehicle.current_position.y else (-1 if target.y < vehicle.current_position.y else 0)
                    
                    new_x = max(0, min(self.city.grid_size[0] - 1, vehicle.current_position.x + dx))
                    new_y = max(0, min(self.city.grid_size[1] - 1, vehicle.current_position.y + dy))
                    
                    vehicle.current_position = Position(new_x, new_y)
        
        # Simulate random breakdown
        if self.simulation_time % 30 == 0:  # Every 30 seconds
            import random
            if random.random() < 0.3:  # 30% chance
                healthy_vehicles = [v for v in self.vehicles.values() if not v.is_broken]
                if healthy_vehicles:
                    random.choice(healthy_vehicles).is_broken = True
                    print("💥 Vehicle breakdown!")
        
        # Simulate passenger arrivals
        if self.simulation_time % 10 == 0:  # Every 10 seconds
            import random
            for station in self.stations.values():
                if random.random() < 0.4 and len(station.passenger_queue) < 15:
                    station.passenger_queue.append(f"passenger_{self.simulation_time}")
    
    async def run_demo(self, duration=60):
        """Run the demonstration for a specified duration"""
        print("🚀 Starting Transportation System Demo")
        print("This demo shows the system visualization without SPADE agents")
        print(f"Demo will run for {duration} seconds...")
        print("\nPress Ctrl+C to stop early\n")
        
        self.setup_demo_agents()
        
        try:
            for _ in range(duration):
                self.update_simulation()
                self.visualizer.render_city(self.vehicles, self.stations)
                
                # Show some metrics
                active_vehicles = sum(1 for v in self.vehicles.values() if not v.is_broken)
                total_passengers = sum(len(s.passenger_queue) for s in self.stations.values())
                
                print(f"\n⏰ Simulation Time: {self.simulation_time}s")
                print(f"Active Vehicles: {active_vehicles}/{len(self.vehicles)}")
                print(f"Total Passengers Waiting: {total_passengers}")
                
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Demo stopped by user")
        
        print("\n✅ Demo completed!")
        print("\nTo run the full SPADE-based simulation:")
        print("1. Set up an XMPP server (or configure for localhost)")
        print("2. Run: python main.py")

async def main():
    demo = DemoSimulation()
    await demo.run_demo(60)  # Run for 60 seconds

if __name__ == "__main__":
    asyncio.run(main())