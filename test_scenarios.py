"""
Automated scenario testing for the transportation system
"""
import asyncio
import random
from datetime import datetime
from typing import Dict, List, Any

from src.environment.city import City
from src.simulation.coordinator import SimulationCoordinator
from src.config.settings import SIMULATION_CONFIG


class ScenarioTester:
    """Test different scenarios in the transportation system"""
    
    def __init__(self):
        self.results = {}
        
    async def run_all_scenarios(self):
        """Run all test scenarios"""
        print("🧪 Starting Scenario Testing Suite")
        print("=" * 60)
        
        scenarios = [
            ("Normal Operations", self.test_normal_operations),
            ("Rush Hour", self.test_rush_hour),
            ("Multiple Breakdowns", self.test_multiple_breakdowns),
            ("High Demand Event", self.test_high_demand_event),
            ("Traffic Congestion", self.test_traffic_congestion),
            ("Resource Shortage", self.test_resource_shortage)
        ]
        
        for scenario_name, scenario_func in scenarios:
            print(f"\n📋 Testing: {scenario_name}")
            print("-" * 60)
            
            try:
                result = await scenario_func()
                self.results[scenario_name] = result
                self.print_scenario_result(scenario_name, result)
            except Exception as e:
                print(f"❌ Scenario failed with error: {e}")
                self.results[scenario_name] = {"status": "failed", "error": str(e)}
        
        self.print_summary()
    
    async def test_normal_operations(self) -> Dict[str, Any]:
        """Test system under normal operating conditions"""
        config = SIMULATION_CONFIG.copy()
        config['simulation']['max_duration'] = 180  # 3 minutes
        
        city = City(config['city'])
        coordinator = SimulationCoordinator(city)
        
        await coordinator.start_simulation()
        
        # Let it run for a bit
        await asyncio.sleep(180)
        
        # Collect metrics
        metrics = await self.collect_metrics(coordinator)
        
        await coordinator.stop_simulation()
        
        return {
            "status": "completed",
            "duration": 180,
            "metrics": metrics
        }
    
    async def test_rush_hour(self) -> Dict[str, Any]:
        """Test system during rush hour with 3x passenger arrival rate"""
        config = SIMULATION_CONFIG.copy()
        config['passenger']['arrival_rate'] = 0.9  # 3x normal
        config['simulation']['max_duration'] = 180
        
        city = City(config['city'])
        coordinator = SimulationCoordinator(city)
        
        # Force rush hour conditions
        for station in coordinator.station_agents.values():
            station.arrival_rate = 0.9
        
        await coordinator.start_simulation()
        await asyncio.sleep(180)
        
        metrics = await self.collect_metrics(coordinator)
        
        await coordinator.stop_simulation()
        
        # Check if system handled high demand well
        avg_waiting = metrics.get('average_waiting_time', 0)
        queue_overflow = metrics.get('queue_overflow_count', 0)
        
        return {
            "status": "completed",
            "duration": 180,
            "metrics": metrics,
            "passed": avg_waiting < 20 and queue_overflow == 0,
            "assessment": "Good" if avg_waiting < 15 else "Needs improvement"
        }
    
    async def test_multiple_breakdowns(self) -> Dict[str, Any]:
        """Test system response to multiple simultaneous vehicle breakdowns"""
        config = SIMULATION_CONFIG.copy()
        config['simulation']['max_duration'] = 180
        
        city = City(config['city'])
        coordinator = SimulationCoordinator(city)
        
        await coordinator.start_simulation()
        
        # Wait 30 seconds then cause breakdowns
        await asyncio.sleep(30)
        
        # Break 30% of vehicles
        num_to_break = max(3, len(coordinator.vehicle_agents) // 3)
        vehicles_to_break = random.sample(list(coordinator.vehicle_agents.values()), num_to_break)
        
        for vehicle in vehicles_to_break:
            vehicle.is_broken = True
            print(f"💥 Simulated breakdown: {vehicle.vehicle_id}")
        
        # Run for another 150 seconds
        await asyncio.sleep(150)
        
        metrics = await self.collect_metrics(coordinator)
        
        # Check maintenance response
        repairs_completed = sum(crew.total_repairs for crew in coordinator.maintenance_agents.values())
        avg_response_time = sum(crew.total_response_time for crew in coordinator.maintenance_agents.values()) / max(1, len(coordinator.maintenance_agents))
        
        await coordinator.stop_simulation()
        
        return {
            "status": "completed",
            "breakdowns_simulated": num_to_break,
            "repairs_completed": repairs_completed,
            "avg_response_time": avg_response_time,
            "metrics": metrics,
            "passed": repairs_completed >= num_to_break // 2,  # At least half repaired
            "assessment": "Good" if avg_response_time < 5 else "Slow response"
        }
    
    async def test_high_demand_event(self) -> Dict[str, Any]:
        """Test system response to sudden demand spike (e.g., concert ending)"""
        config = SIMULATION_CONFIG.copy()
        config['simulation']['max_duration'] = 180
        
        city = City(config['city'])
        coordinator = SimulationCoordinator(city)
        
        await coordinator.start_simulation()
        await asyncio.sleep(60)
        
        # Create demand spike at 3 stations
        spike_stations = random.sample(list(coordinator.station_agents.values()), 3)
        
        print(f"🎭 Simulating event ending - demand spike at 3 stations")
        
        for station in spike_stations:
            # Add 30 passengers instantly
            for i in range(30):
                passenger_id = f"event_passenger_{station.station_id}_{i}"
                passenger_info = {
                    'id': passenger_id,
                    'arrival_time': datetime.now(),
                    'origin': station.position,
                    'destination': random.choice([s.position for s in coordinator.station_agents.values() if s != station]),
                    'patience_time': 20
                }
                station.passenger_queue.append(passenger_info)
        
        # Run simulation
        await asyncio.sleep(120)
        
        metrics = await self.collect_metrics(coordinator)
        
        # Check how well system adapted
        contract_net_activations = sum(s.service_requests_sent for s in coordinator.station_agents.values())
        
        await coordinator.stop_simulation()
        
        return {
            "status": "completed",
            "spike_stations": len(spike_stations),
            "passengers_added": 90,
            "contract_net_activations": contract_net_activations,
            "metrics": metrics,
            "passed": contract_net_activations >= 3,  # Stations should request help
            "assessment": "Good adaptation" if contract_net_activations >= 5 else "Limited adaptation"
        }
    
    async def test_traffic_congestion(self) -> Dict[str, Any]:
        """Test system under heavy traffic conditions"""
        config = SIMULATION_CONFIG.copy()
        config['simulation']['max_duration'] = 180
        
        city = City(config['city'])
        
        # Set high traffic everywhere
        for position in city.traffic_conditions:
            city.traffic_conditions[position] = random.uniform(0.7, 0.95)
        
        coordinator = SimulationCoordinator(city)
        
        await coordinator.start_simulation()
        await asyncio.sleep(180)
        
        metrics = await self.collect_metrics(coordinator)
        
        # Check route adaptations
        route_adaptations = 0
        for vehicle in coordinator.vehicle_agents.values():
            if hasattr(vehicle, 'route_adapter') and vehicle.route_adapter:
                stats = vehicle.route_adapter.get_adaptation_stats()
                route_adaptations += stats.get('total_adaptations', 0)
        
        await coordinator.stop_simulation()
        
        return {
            "status": "completed",
            "route_adaptations": route_adaptations,
            "metrics": metrics,
            "passed": route_adaptations > 0,  # Should adapt to traffic
            "assessment": "Good" if route_adaptations >= 5 else "Limited adaptation"
        }
    
    async def test_resource_shortage(self) -> Dict[str, Any]:
        """Test system with limited resources (few vehicles, maintenance crews)"""
        config = SIMULATION_CONFIG.copy()
        config['city']['num_vehicles'] = 5  # Reduced from 10
        config['city']['num_maintenance_crews'] = 1  # Reduced from 3
        config['simulation']['max_duration'] = 180
        
        city = City(config['city'])
        coordinator = SimulationCoordinator(city)
        
        await coordinator.start_simulation()
        await asyncio.sleep(180)
        
        metrics = await self.collect_metrics(coordinator)
        
        await coordinator.stop_simulation()
        
        # System should struggle but not collapse
        fleet_util = metrics.get('fleet_utilization', 0)
        avg_waiting = metrics.get('average_waiting_time', 0)
        
        return {
            "status": "completed",
            "limited_vehicles": 5,
            "limited_maintenance": 1,
            "metrics": metrics,
            "passed": fleet_util > 0.8 and avg_waiting < 25,  # High utilization expected
            "assessment": "System strained but functional" if fleet_util > 0.8 else "System overloaded"
        }
    
    async def collect_metrics(self, coordinator: SimulationCoordinator) -> Dict[str, Any]:
        """Collect metrics from the simulation"""
        
        # Vehicle metrics
        active_vehicles = sum(1 for v in coordinator.vehicle_agents.values() if not v.is_broken)
        total_vehicles = len(coordinator.vehicle_agents)
        fleet_utilization = active_vehicles / total_vehicles if total_vehicles > 0 else 0
        
        # Station metrics
        total_waiting = sum(len(s.passenger_queue) for s in coordinator.station_agents.values())
        total_waiting_time = sum(s.total_waiting_time for s in coordinator.station_agents.values())
        total_served = sum(s.total_passengers_served for s in coordinator.station_agents.values())
        avg_waiting_time = total_waiting_time / total_served if total_served > 0 else 0
        
        # Performance metrics
        total_on_time = sum(v.on_time_arrivals for v in coordinator.vehicle_agents.values())
        total_arrivals = sum(v.total_arrivals for v in coordinator.vehicle_agents.values())
        on_time_performance = total_on_time / total_arrivals if total_arrivals > 0 else 0
        
        return {
            "fleet_utilization": fleet_utilization,
            "average_waiting_time": avg_waiting_time,
            "on_time_performance": on_time_performance,
            "passengers_waiting": total_waiting,
            "passengers_served": total_served,
            "active_vehicles": active_vehicles,
            "total_vehicles": total_vehicles
        }
    
    def print_scenario_result(self, name: str, result: Dict[str, Any]):
        """Print scenario test result"""
        if result.get("status") == "completed":
            print(f"✅ Scenario completed")
            
            if "metrics" in result:
                metrics = result["metrics"]
                print(f"   Fleet Utilization: {metrics.get('fleet_utilization', 0):.1%}")
                print(f"   Avg Waiting Time: {metrics.get('average_waiting_time', 0):.1f} min")
                print(f"   On-Time Performance: {metrics.get('on_time_performance', 0):.1%}")
                print(f"   Passengers Served: {metrics.get('passengers_served', 0)}")
            
            if "passed" in result:
                status = "✅ PASSED" if result["passed"] else "❌ FAILED"
                print(f"   Test Result: {status}")
            
            if "assessment" in result:
                print(f"   Assessment: {result['assessment']}")
        else:
            print(f"❌ Scenario failed: {result.get('error', 'Unknown error')}")
    
    def print_summary(self):
        """Print overall test summary"""
        print("\n" + "=" * 60)
        print("📊 SCENARIO TESTING SUMMARY")
        print("=" * 60)
        
        total = len(self.results)
        completed = sum(1 for r in self.results.values() if r.get("status") == "completed")
        passed = sum(1 for r in self.results.values() if r.get("passed", False))
        
        print(f"Total Scenarios: {total}")
        print(f"Completed: {completed}")
        print(f"Passed: {passed}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        
        print("\nDetailed Results:")
        for name, result in self.results.items():
            status = "✅" if result.get("passed", False) else ("⚠️" if result.get("status") == "completed" else "❌")
            print(f"  {status} {name}")
        
        print("\n" + "=" * 60)


async def main():
    """Run scenario tests"""
    tester = ScenarioTester()
    await tester.run_all_scenarios()


if __name__ == "__main__":
    asyncio.run(main())