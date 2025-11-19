"""
Metrics collector for transportation system - functional version
"""
from datetime import datetime
from typing import Dict, Any, List

class MetricsCollector:
    """Comprehensive metrics collector for transportation system"""
    
    def __init__(self):
        self.metrics = {}
        
        # Aggregate metrics
        self.total_passengers_served = 0
        self.total_waiting_time = 0.0
        self.waiting_time_samples = 0
        
        self.total_breakdowns = 0
        self.breakdown_response_times = []
        
        self.contract_net_activations = 0
        self.contracts_awarded = 0
        
        self.on_time_arrivals = 0
        self.total_arrivals = 0
        
        self.route_adaptations = 0
    
    def collect(self, agent_id: str, metric_name: str, value: Any):
        """Collect generic metric"""
        if agent_id not in self.metrics:
            self.metrics[agent_id] = {}
        self.metrics[agent_id][metric_name] = {
            'value': value,
            'timestamp': datetime.now()
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        return self.metrics
    
    # PASSO 5: Specific metric recording methods
    
    def record_passenger_served(self, station_id: str, waiting_time: float):
        """Record a passenger being served"""
        self.total_passengers_served += 1
        self.total_waiting_time += waiting_time
        self.waiting_time_samples += 1
        
        self.collect(station_id, 'passengers_served', self.total_passengers_served)
    
    def record_breakdown_response_time(self, vehicle_id: str, crew_id: str, response_time: float, repair_time: float):
        """Record maintenance response and repair time"""
        self.total_breakdowns += 1
        self.breakdown_response_times.append(response_time)
        
        self.collect(vehicle_id, 'breakdown_resolved', {
            'crew_id': crew_id,
            'response_time': response_time,
            'repair_time': repair_time
        })
    
    def record_contract_net_activation(self, station_id: str, demand_level: int):
        """Record Contract Net Protocol activation"""
        self.contract_net_activations += 1
        
        self.collect(station_id, 'cnp_activated', {
            'activation_count': self.contract_net_activations,
            'demand_level': demand_level
        })
    
    def record_contract_awarded(self, station_id: str, vehicle_id: str):
        """Record contract awarded in CNP"""
        self.contracts_awarded += 1
        
        self.collect(station_id, 'contract_awarded', {
            'vehicle_id': vehicle_id,
            'total_contracts': self.contracts_awarded
        })
    
    def record_vehicle_arrival(self, vehicle_id: str, on_time: bool):
        """Record vehicle arrival at station"""
        self.total_arrivals += 1
        if on_time:
            self.on_time_arrivals += 1
        
        self.collect(vehicle_id, 'arrival', {
            'on_time': on_time,
            'on_time_rate': self.on_time_arrivals / max(1, self.total_arrivals)
        })
    
    def record_route_adaptation(self, vehicle_id: str):
        """Record dynamic route adaptation"""
        self.route_adaptations += 1
        
        self.collect(vehicle_id, 'route_adapted', self.route_adaptations)
    
    def get_current_performance_summary(self, agents_registry: Dict) -> Dict[str, Any]:
        """Get comprehensive performance summary for dashboard"""
        
        # Calculate average waiting time
        avg_waiting_time = (
            self.total_waiting_time / self.waiting_time_samples 
            if self.waiting_time_samples > 0 else 0
        )
        
        # Calculate average breakdown response time
        avg_breakdown_response = (
            sum(self.breakdown_response_times) / len(self.breakdown_response_times)
            if self.breakdown_response_times else 0
        )
        
        # Calculate on-time performance
        on_time_performance = (
            (self.on_time_arrivals / self.total_arrivals * 100)
            if self.total_arrivals > 0 else 100
        )
        
        # Calculate fleet utilization (vehicles with passengers vs total)
        vehicles = [a for k, a in agents_registry.items() if 'vehicle' in k]
        vehicles_with_passengers = sum(1 for v in vehicles if hasattr(v, 'occupancy') and v.occupancy > 0)
        fleet_utilization = (
            (vehicles_with_passengers / len(vehicles) * 100)
            if vehicles else 0
        )
        
        # Count broken vehicles
        broken_vehicles = sum(1 for v in vehicles if hasattr(v, 'is_broken') and v.is_broken)
        
        # Passenger satisfaction (inverse of waiting time, normalized)
        passenger_satisfaction = max(0, min(100, 100 - (avg_waiting_time * 5)))
        
        return {
            'total_agents': len(agents_registry),
            'stations': sum(1 for k in agents_registry if 'station' in k),
            'vehicles': sum(1 for k in agents_registry if 'vehicle' in k),
            'passengers': sum(1 for k in agents_registry if 'passenger' in k),
            'maintenance': sum(1 for k in agents_registry if 'maint' in k),
            
            # Performance metrics
            'total_passengers_served': self.total_passengers_served,
            'avg_waiting_time': round(avg_waiting_time, 2),
            'passenger_satisfaction': round(passenger_satisfaction, 1),
            
            # Fleet metrics
            'fleet_utilization': round(fleet_utilization, 1),
            'vehicles_on_time': round(on_time_performance, 1),
            'on_time_arrivals': self.on_time_arrivals,
            'total_arrivals': self.total_arrivals,
            
            # Breakdown metrics
            'total_breakdowns': self.total_breakdowns,
            'avg_breakdown_response': round(avg_breakdown_response, 2),
            'broken_vehicles': broken_vehicles,
            
            # Collaboration metrics
            'contract_net_activations': self.contract_net_activations,
            'contracts_awarded': self.contracts_awarded,
            'route_adaptations': self.route_adaptations,
        }

