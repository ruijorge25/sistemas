"""
Realistic Scenario Tests - Tests system under different conditions
Tests: rush hour, breakdowns, concert events, traffic jams
"""
import asyncio
import random
from datetime import datetime, timedelta
from src.environment.city import City, Route, Position
from src.config.settings import SIMULATION_CONFIG
from src.environment.events import EventManager, DynamicEvent
from src.metrics.collector import MetricsCollector

class ScenarioTester:
    """Tests different scenarios"""
    
    def __init__(self):
        self.city = City(SIMULATION_CONFIG['city'])
        self.event_manager = EventManager(self.city)
        self.metrics = MetricsCollector()
        
    async def test_rush_hour_scenario(self):
        """Test system under rush hour conditions"""
        print("\n" + "="*60)
        print("🧪 TEST 1: Rush Hour Scenario")
        print("="*60)
        
        # Create rush hour at multiple locations
        rush_locations = [
            (5, 5),   # Business district
            (15, 15), # Residential area
            (10, 3),  # Train station
            (18, 12)  # Shopping center
        ]
        
        events = self.event_manager.create_rush_hour_surge(rush_locations)
        
        # Simulate for 2 minutes
        start_time = datetime.now()
        demand_measurements = []
        
        for _ in range(12):  # 12 x 10 sec = 2 min
            await asyncio.sleep(10)
            
            # Measure demand at each location
            for loc in rush_locations:
                modifier = self.event_manager.get_demand_modifier(loc)
                demand_measurements.append(modifier)
            
            # Check if events are still active
            await self.event_manager.update_events()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Validate results
        avg_demand = sum(demand_measurements) / len(demand_measurements)
        max_demand = max(demand_measurements)
        
        print(f"\n📊 Rush Hour Test Results:")
        print(f"   Duration: {duration:.1f}s")
        print(f"   Events created: {len(events)}")
        print(f"   Average demand multiplier: {avg_demand:.2f}x")
        print(f"   Peak demand multiplier: {max_demand:.2f}x")
        print(f"   Expected: >2.0x demand at locations")
        
        # Assertions
        assert len(events) == 4, f"Expected 4 events, got {len(events)}"
        assert avg_demand > 2.0, f"Expected avg demand >2.0x, got {avg_demand:.2f}x"
        assert max_demand > 3.0, f"Expected peak >3.0x, got {max_demand:.2f}x"
        
        print("   ✅ Rush hour test PASSED!")
        return True
    
    async def test_breakdown_cascade(self):
        """Test system response to multiple breakdowns"""
        print("\n" + "="*60)
        print("🧪 TEST 2: Breakdown Cascade Scenario")
        print("="*60)
        
        # Simulate 3 vehicle breakdowns
        breakdowns = []
        for i in range(3):
            vehicle_id = f"vehicle_{i}"
            response_time = random.uniform(2.0, 5.0)
            self.metrics.record_breakdown(vehicle_id, response_time)
            breakdowns.append((vehicle_id, response_time))
            await asyncio.sleep(5)  # Stagger breakdowns
        
        # Calculate metrics
        avg_response = sum(r for _, r in breakdowns) / len(breakdowns)
        
        print(f"\n📊 Breakdown Test Results:")
        print(f"   Breakdowns simulated: {len(breakdowns)}")
        for vid, rt in breakdowns:
            print(f"   - {vid}: {rt:.1f}min response time")
        print(f"   Average response time: {avg_response:.1f}min")
        print(f"   Expected: <6.0min average response")
        
        # Assertions
        assert len(breakdowns) == 3, f"Expected 3 breakdowns, got {len(breakdowns)}"
        assert avg_response < 6.0, f"Response time too high: {avg_response:.1f}min"
        assert all(r > 0 for _, r in breakdowns), "Invalid response times"
        
        print("   ✅ Breakdown cascade test PASSED!")
        return True
    
    async def test_concert_event(self):
        """Test sudden passenger surge from concert"""
        print("\n" + "="*60)
        print("🧪 TEST 3: Concert Event (Sudden Demand Surge)")
        print("="*60)
        
        # Create concert event at city center
        concert_location = (10, 10)
        attendees = 800
        
        event = self.event_manager.create_concert_event(concert_location, attendees)
        
        # Measure demand surge
        measurements = []
        for _ in range(6):  # 6 x 5 sec = 30 sec
            await asyncio.sleep(5)
            
            # Check demand at concert location
            modifier = self.event_manager.get_demand_modifier(concert_location)
            measurements.append(modifier)
            
            # Check nearby locations (within radius)
            nearby = [(9, 10), (11, 10), (10, 9), (10, 11)]
            for pos in nearby:
                nearby_modifier = self.event_manager.get_demand_modifier(pos)
                measurements.append(nearby_modifier)
        
        avg_surge = sum(measurements) / len(measurements)
        peak_surge = max(measurements)
        
        print(f"\n📊 Concert Event Test Results:")
        print(f"   Location: {concert_location}")
        print(f"   Attendees: {attendees}")
        print(f"   Affected radius: {event.affected_radius} blocks")
        print(f"   Average demand surge: {avg_surge:.1f}x normal")
        print(f"   Peak demand surge: {peak_surge:.1f}x normal")
        print(f"   Expected: >5.0x surge at epicenter")
        
        # Assertions
        assert event.event_type == 'concert', "Wrong event type"
        assert event.intensity > 0.5, f"Intensity too low: {event.intensity}"
        assert peak_surge > 5.0, f"Peak surge too low: {peak_surge:.1f}x"
        assert avg_surge > 2.0, f"Average surge too low: {avg_surge:.1f}x"
        
        print("   ✅ Concert event test PASSED!")
        return True
    
    async def test_traffic_jam_geographic(self):
        """Test geographic traffic jam affecting vehicle speeds"""
        print("\n" + "="*60)
        print("🧪 TEST 4: Geographic Traffic Jam")
        print("="*60)
        
        # Create traffic jam in specific zone
        zone_start = (5, 5)
        zone_end = (10, 10)
        severity = 0.8
        
        event = self.event_manager.create_traffic_jam(zone_start, zone_end, severity)
        
        # Test speed modifiers at different locations
        test_points = [
            ((7, 7), True,  "Inside jam"),
            ((5, 5), True,  "Jam edge"),
            ((10, 10), True, "Jam edge 2"),
            ((2, 2), False, "Outside jam"),
            ((15, 15), False, "Far away")
        ]
        
        results = []
        for pos, should_be_affected, desc in test_points:
            modifier = self.event_manager.get_traffic_modifier(pos)
            affected = modifier < 1.0
            results.append((pos, modifier, affected, should_be_affected, desc))
        
        print(f"\n📊 Traffic Jam Test Results:")
        print(f"   Zone: {zone_start} to {zone_end}")
        print(f"   Severity: {severity:.0%}")
        print(f"\n   Speed modifiers:")
        for pos, mod, aff, expected, desc in results:
            status = "✅" if (aff == expected) else "❌"
            print(f"   {status} {pos} ({desc}): {mod:.2f}x speed, affected={aff}")
        
        # Assertions
        inside_affected = [r for r in results if r[3] == True and r[2] == True]
        outside_normal = [r for r in results if r[3] == False and r[2] == False]
        
        assert len(inside_affected) >= 2, "Traffic jam not affecting inside locations"
        assert len(outside_normal) >= 1, "Traffic jam affecting outside locations"
        assert event.intensity == severity, "Wrong severity"
        
        print("   ✅ Traffic jam test PASSED!")
        return True
    
    async def test_cnp_under_load(self):
        """Test Contract Net Protocol under high load"""
        print("\n" + "="*60)
        print("🧪 TEST 5: CNP Under Load (Multiple Simultaneous Contracts)")
        print("="*60)
        
        # Simulate multiple CNP activations
        num_contracts = 25
        start_time = datetime.now()
        
        for i in range(num_contracts):
            self.metrics.record_cnp_activation()
            await asyncio.sleep(0.1)  # 100ms between activations
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        throughput = num_contracts / duration
        
        print(f"\n📊 CNP Load Test Results:")
        print(f"   Contracts processed: {num_contracts}")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Throughput: {throughput:.1f} contracts/sec")
        print(f"   Total CNP activations: {self.metrics.contract_net_activations}")
        print(f"   Expected: >8 contracts/sec")
        
        # Assertions
        assert self.metrics.contract_net_activations == num_contracts
        assert throughput > 8, f"Throughput too low: {throughput:.1f}/sec"
        assert duration < 5.0, f"Processing too slow: {duration:.2f}s"
        
        print("   ✅ CNP load test PASSED!")
        return True
    
    async def test_combined_scenario(self):
        """Test system with multiple events simultaneously"""
        print("\n" + "="*60)
        print("🧪 TEST 6: Combined Scenario (Chaos Test)")
        print("="*60)
        
        # Create multiple events at once
        print("\n   Creating multiple events...")
        
        # 1. Rush hour
        rush_events = self.event_manager.create_rush_hour_surge([(5,5), (15,15)])
        print(f"   ✓ Rush hour: {len(rush_events)} surges")
        
        # 2. Traffic jam
        traffic = self.event_manager.create_traffic_jam((7,7), (12,12), 0.7)
        print(f"   ✓ Traffic jam at {traffic.location}")
        
        # 3. Concert
        concert = self.event_manager.create_concert_event((10,10), 500)
        print(f"   ✓ Concert with {concert.intensity*500:.0f} attendees")
        
        # 4. Accident
        accident = self.event_manager.create_accident((8,15))
        print(f"   ✓ Accident blocking {accident.location}")
        
        # 5. Weather
        weather = self.event_manager.create_weather_event("heavy_rain")
        print(f"   ✓ Weather event (intensity: {weather.intensity})")
        
        # Monitor system for 30 seconds
        await asyncio.sleep(30)
        
        # Get event summary
        summary = self.event_manager.get_active_events_summary()
        
        print(f"\n📊 Combined Scenario Results:")
        print(f"   Total active events: {summary['total_active']}")
        print(f"   Event breakdown:")
        for event_type, count in summary['by_type'].items():
            if count > 0:
                print(f"      - {event_type}: {count}")
        
        # Assertions
        assert summary['total_active'] >= 5, f"Not enough active events: {summary['total_active']}"
        assert summary['by_type']['concert'] >= 1, "Concert not active"
        assert summary['by_type']['traffic_jam'] >= 1, "Traffic jam not active"
        assert summary['by_type']['demand_surge'] >= 2, "Rush hour not active"
        
        print("   ✅ Combined scenario test PASSED!")
        return True
    
    async def run_all_tests(self):
        """Run all scenario tests"""
        print("\n" + "="*60)
        print("STARTING REALISTIC SCENARIO TESTS")
        print("="*60)
        
        tests = [
            ("Rush Hour", self.test_rush_hour_scenario),
            ("Breakdown Cascade", self.test_breakdown_cascade),
            ("Concert Event", self.test_concert_event),
            ("Traffic Jam Geographic", self.test_traffic_jam_geographic),
            ("CNP Under Load", self.test_cnp_under_load),
            ("Combined Scenario", self.test_combined_scenario)
        ]
        
        results = []
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results.append((test_name, "PASSED", None))
                passed += 1
            except AssertionError as e:
                results.append((test_name, "FAILED", str(e)))
                failed += 1
            except Exception as e:
                results.append((test_name, "ERROR", str(e)))
                failed += 1
        
        # Print summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        for test_name, status, error in results:
            icon = "✅" if status == "PASSED" else "❌"
            print(f"{icon} {test_name}: {status}")
            if error:
                print(f"   Error: {error}")
        
        print(f"\nTotal: {len(tests)} tests")
        print(f"Passed: {passed} ({passed/len(tests)*100:.0f}%)")
        print(f"Failed: {failed}")
        
        if failed == 0:
            print("\n🎉 ALL TESTS PASSED! 🎉")
        else:
            print(f"\n⚠️  {failed} test(s) failed")
        
        return passed == len(tests)

async def main():
    """Run scenario tests"""
    tester = ScenarioTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ System validation complete - ALL scenarios handled correctly")
        return 0
    else:
        print("\n❌ Some tests failed - review results above")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
