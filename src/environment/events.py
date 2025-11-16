"""
Dynamic Event System for realistic urban scenarios
Handles concerts, traffic jams, demand surges, etc.
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

@dataclass
class DynamicEvent:
    """Represents a dynamic event in the city"""
    event_id: str
    event_type: str  # 'concert', 'traffic_jam', 'weather', 'accident'
    location: Tuple[int, int]  # (x, y)
    start_time: datetime
    duration: timedelta
    intensity: float  # 0.0 to 1.0
    affected_radius: int
    active: bool = True

class EventManager:
    """Manages dynamic events in the simulation"""
    
    def __init__(self, city):
        self.city = city
        self.active_events = []
        self.event_history = []
        self.event_counter = 0
        
    def create_concert_event(self, location: Tuple[int, int], 
                            attendees: int = 500) -> DynamicEvent:
        """Create a concert ending event - sudden passenger surge"""
        self.event_counter += 1
        
        event = DynamicEvent(
            event_id=f"concert_{self.event_counter}",
            event_type="concert",
            location=location,
            start_time=datetime.now(),
            duration=timedelta(minutes=30),  # 30min surge
            intensity=min(1.0, attendees / 500),  # Scale by attendees
            affected_radius=3  # 3 blocks radius
        )
        
        self.active_events.append(event)
        print(f"🎵 Concert ending at {location}! {attendees} passengers incoming")
        
        return event
    
    def create_traffic_jam(self, zone_start: Tuple[int, int], 
                          zone_end: Tuple[int, int],
                          severity: float = 0.7) -> DynamicEvent:
        """Create geographic traffic jam affecting vehicle speed"""
        self.event_counter += 1
        
        center_x = (zone_start[0] + zone_end[0]) // 2
        center_y = (zone_start[1] + zone_end[1]) // 2
        
        event = DynamicEvent(
            event_id=f"traffic_{self.event_counter}",
            event_type="traffic_jam",
            location=(center_x, center_y),
            start_time=datetime.now(),
            duration=timedelta(minutes=random.randint(15, 45)),
            intensity=severity,
            affected_radius=max(abs(zone_end[0] - zone_start[0]), 
                               abs(zone_end[1] - zone_start[1]))
        )
        
        self.active_events.append(event)
        print(f"🚦 Traffic jam from {zone_start} to {zone_end}, severity: {severity:.1%}")
        
        return event
    
    def create_weather_event(self, event_subtype: str = "rain") -> DynamicEvent:
        """Create city-wide weather event affecting all vehicles"""
        self.event_counter += 1
        
        intensity_map = {
            "rain": 0.3,
            "heavy_rain": 0.6,
            "snow": 0.7,
            "fog": 0.4
        }
        
        event = DynamicEvent(
            event_id=f"weather_{self.event_counter}",
            event_type="weather",
            location=(10, 10),  # City center
            start_time=datetime.now(),
            duration=timedelta(minutes=random.randint(30, 90)),
            intensity=intensity_map.get(event_subtype, 0.5),
            affected_radius=999  # City-wide
        )
        
        self.active_events.append(event)
        print(f"🌧️ Weather event: {event_subtype}, duration: {event.duration.seconds//60}min")
        
        return event
    
    def create_accident(self, location: Tuple[int, int]) -> DynamicEvent:
        """Create accident blocking route"""
        self.event_counter += 1
        
        event = DynamicEvent(
            event_id=f"accident_{self.event_counter}",
            event_type="accident",
            location=location,
            start_time=datetime.now(),
            duration=timedelta(minutes=random.randint(20, 60)),
            intensity=1.0,  # Complete blockage
            affected_radius=1  # Immediate area
        )
        
        self.active_events.append(event)
        print(f"🚨 Accident at {location}! Route blocked for {event.duration.seconds//60}min")
        
        return event
    
    def create_rush_hour_surge(self, peak_locations: List[Tuple[int, int]]) -> List[DynamicEvent]:
        """Create multiple demand surges at key locations"""
        events = []
        
        for i, location in enumerate(peak_locations):
            self.event_counter += 1
            
            event = DynamicEvent(
                event_id=f"rush_hour_{self.event_counter}",
                event_type="demand_surge",
                location=location,
                start_time=datetime.now(),
                duration=timedelta(minutes=60),
                intensity=0.8,
                affected_radius=2
            )
            
            self.active_events.append(event)
            events.append(event)
        
        print(f"🏢 Rush hour! {len(events)} demand surges at key locations")
        return events
    
    def is_location_affected(self, location: Tuple[int, int], 
                            event_type: str = None) -> Tuple[bool, float]:
        """Check if location is affected by any event"""
        max_intensity = 0.0
        affected = False
        
        for event in self.active_events:
            if event_type and event.event_type != event_type:
                continue
            
            # Calculate distance
            distance = ((location[0] - event.location[0])**2 + 
                       (location[1] - event.location[1])**2)**0.5
            
            if distance <= event.affected_radius:
                affected = True
                # Intensity decreases with distance
                intensity_factor = 1.0 - (distance / event.affected_radius)
                effective_intensity = event.intensity * intensity_factor
                max_intensity = max(max_intensity, effective_intensity)
        
        return affected, max_intensity
    
    def get_traffic_modifier(self, location: Tuple[int, int]) -> float:
        """Get speed modifier for vehicle at location (1.0 = normal, <1.0 = slower)"""
        affected, intensity = self.is_location_affected(location, "traffic_jam")
        
        if affected:
            # Traffic reduces speed: intensity 1.0 = 30% speed, 0.5 = 65% speed
            return 1.0 - (intensity * 0.7)
        
        # Check weather
        affected_weather, weather_intensity = self.is_location_affected(location, "weather")
        if affected_weather:
            return 1.0 - (weather_intensity * 0.5)
        
        return 1.0  # Normal speed
    
    def get_demand_modifier(self, location: Tuple[int, int]) -> float:
        """Get passenger demand modifier at location (1.0 = normal, >1.0 = surge)"""
        # Check for concert events
        affected_concert, concert_intensity = self.is_location_affected(location, "concert")
        if affected_concert:
            return 1.0 + (concert_intensity * 10.0)  # Up to 11x demand!
        
        # Check for demand surge
        affected_surge, surge_intensity = self.is_location_affected(location, "demand_surge")
        if affected_surge:
            return 1.0 + (surge_intensity * 3.0)  # Up to 4x demand
        
        return 1.0  # Normal demand
    
    def is_route_blocked(self, location: Tuple[int, int]) -> bool:
        """Check if route is blocked by accident"""
        affected, intensity = self.is_location_affected(location, "accident")
        return affected and intensity > 0.8
    
    async def update_events(self):
        """Update and expire events"""
        now = datetime.now()
        expired = []
        
        for event in self.active_events:
            if now > event.start_time + event.duration:
                expired.append(event)
                event.active = False
                self.event_history.append(event)
                print(f"⏰ Event {event.event_id} ({event.event_type}) expired")
        
        for event in expired:
            self.active_events.remove(event)
    
    def get_active_events_summary(self) -> Dict[str, Any]:
        """Get summary of active events"""
        return {
            'total_active': len(self.active_events),
            'by_type': {
                'concert': sum(1 for e in self.active_events if e.event_type == 'concert'),
                'traffic_jam': sum(1 for e in self.active_events if e.event_type == 'traffic_jam'),
                'weather': sum(1 for e in self.active_events if e.event_type == 'weather'),
                'accident': sum(1 for e in self.active_events if e.event_type == 'accident'),
                'demand_surge': sum(1 for e in self.active_events if e.event_type == 'demand_surge'),
            },
            'events': [
                {
                    'id': e.event_id,
                    'type': e.event_type,
                    'location': e.location,
                    'intensity': e.intensity,
                    'remaining_minutes': ((e.start_time + e.duration) - datetime.now()).seconds // 60
                }
                for e in self.active_events
            ]
        }

class EventScheduler:
    """Schedules realistic events during simulation"""
    
    def __init__(self, event_manager: EventManager):
        self.event_manager = event_manager
        self.running = False
        
    async def run_realistic_scenario(self):
        """Run a realistic day with scheduled events"""
        self.running = True
        
        print("🎬 Starting realistic scenario with scheduled events...")
        
        # Schedule initial rush hour (morning)
        await asyncio.sleep(10)  # 10 sec = morning rush
        rush_locations = [(5, 5), (15, 15), (10, 3), (3, 18)]
        self.event_manager.create_rush_hour_surge(rush_locations)
        
        # Random traffic jams
        await asyncio.sleep(30)
        self.event_manager.create_traffic_jam((7, 7), (12, 12), severity=0.6)
        
        # Concert event
        await asyncio.sleep(45)
        self.event_manager.create_concert_event((10, 10), attendees=800)
        
        # Weather change
        await asyncio.sleep(60)
        self.event_manager.create_weather_event("heavy_rain")
        
        # Accident
        await asyncio.sleep(80)
        self.event_manager.create_accident((8, 15))
        
        # Evening rush
        await asyncio.sleep(100)
        self.event_manager.create_rush_hour_surge([(15, 15), (5, 5)])
        
        # Continuous event updates
        while self.running:
            await self.event_manager.update_events()
            
            # Random events
            if random.random() < 0.05:  # 5% chance every cycle
                event_type = random.choice(['traffic_jam', 'accident'])
                if event_type == 'traffic_jam':
                    x1, y1 = random.randint(0, 15), random.randint(0, 15)
                    x2, y2 = x1 + random.randint(2, 5), y1 + random.randint(2, 5)
                    self.event_manager.create_traffic_jam((x1, y1), (x2, y2))
                else:
                    loc = (random.randint(0, 19), random.randint(0, 19))
                    self.event_manager.create_accident(loc)
            
            await asyncio.sleep(30)  # Check every 30 sec
    
    def stop(self):
        """Stop the event scheduler"""
        self.running = False
