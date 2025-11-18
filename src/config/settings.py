# Configuration for the Multi-Agent Transportation System

SIMULATION_CONFIG = {
    'city': {
        'name': 'SimCity Transport',
        'grid_size': (20, 20),  # 20x20 grid
        'num_stations': 15,
        'num_vehicles': 10,
        'num_passengers': 50,
        'num_maintenance_crews': 3
    },
    'vehicle': {
        'bus_capacity': 60,  # passengers per bus
        'tram_capacity': 40,  # passengers per tram
        'fuel_capacity': 100,
        'fuel_consumption_per_cell': 1,  # 1 unit per cell moved
        'fuel_consumption_rate': 0.5,  # fuel per movement
        'speed': 1,  # grid units per time unit
        'breakdown_probability': 0.02,  # 2% per check - REALISTIC RATE
        'overcrowding_penalty_bus': 50,  # passengers > this = penalty
        'overcrowding_penalty_tram': 35  # passengers > this = penalty
    },
    'station': {
        'max_queue_size': 100,
        'demand_forecast_window': 10,  # time units
        'overcrowding_threshold': 20  # passengers
    },
    'passenger': {
        'patience_time': 15,  # max waiting time
        'arrival_rate': 0.8,  # passengers per time unit per station (INCREASED for visible activity)
        'rush_hour_multiplier': 3.0
    },
    'maintenance': {
        'repair_time_tire': 2,  # time units for tire repair
        'repair_time_engine': 7,  # time units for engine repair
        'repair_time_tow': 3,  # time units for tow operation
        'tools_for_tire': 2,  # tools needed for tire repair
        'tools_for_engine': 5,  # tools needed for engine repair
        'tow_hooks_for_tow': 1,  # tow hooks needed
        'max_concurrent_repairs': 3,
        'response_time': 2,  # time to reach broken vehicle
        'base_tools': 8,  # total tools at maintenance base
        'base_tow_hooks': 2  # total tow hooks at maintenance base
    },
    'simulation': {
        'time_step': 1.0,  # seconds per simulation step
        'max_duration': 3600,  # maximum simulation time
        'rush_hours': [(7, 9), (17, 19)],  # (start, end) hours
        'log_level': 'INFO'
    },
    'weather': {
        'rain_speed_reduction': 0.5,  # 50% speed reduction in rain
        'rain_breakdown_increase': 0.2  # 20% more breakdowns in rain
    },
    'bases': {
        'bus_entry_point': (0, 10),
        'tram_entry_point': (19, 10),
        'maintenance_entry_point': (10, 0)
    }
}

# XMPP Configuration for SPADE agents
XMPP_CONFIG = {
    'server': 'localhost',
    'domain': 'localhost',
    'password': 'password'
}

# Message types for agent communication
MESSAGE_TYPES = {
    'PASSENGER_REQUEST': 'passenger_request',
    'VEHICLE_CAPACITY': 'vehicle_capacity',
    'STATION_DEMAND': 'station_demand',
    'BREAKDOWN_ALERT': 'breakdown_alert',
    'MAINTENANCE_REQUEST': 'maintenance_request',
    'ROUTE_UPDATE': 'route_update',
    'CONTRACT_NET_CFP': 'cfp',  # Call for Proposals
    'CONTRACT_NET_PROPOSE': 'propose',
    'CONTRACT_NET_ACCEPT': 'accept',
    'CONTRACT_NET_REJECT': 'reject',
    'CONTRACT_NET_INFORM': 'inform',  # Inform about contract execution
    'RETURN_TO_BASE': 'return_to_base',
    'DEPLOY_FROM_BASE': 'deploy_from_base'
}

# Breakdown types
BREAKDOWN_TYPES = {
    'TIRE': 'tire',  # Requires 2 tools, 2 seconds
    'ENGINE': 'engine',  # Requires 5 tools, 7 seconds
    'TOW': 'tow'  # Requires 1 tow hook, 3 seconds
}

# Performance metrics to track
METRICS = [
    'average_waiting_time',
    'fleet_utilization',
    'on_time_performance',
    'passenger_satisfaction',
    'collaboration_effectiveness',
    'fuel_efficiency',
    'breakdown_response_time'
]