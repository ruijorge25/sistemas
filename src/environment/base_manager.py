"""
Base Manager for off-grid vehicle and maintenance depots
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from ..environment.city import Position

@dataclass
class BaseConfig:
    """Configuration for a vehicle/maintenance base"""
    name: str
    base_type: str  # 'bus', 'tram', 'maintenance'
    entry_point: Position  # Where vehicles spawn/despawn
    
    # Resources (for maintenance base)
    max_vehicles: int = 0
    tools: int = 0
    tow_hooks: int = 0

class BaseManager:
    """Manages the three off-grid bases"""
    
    def __init__(self):
        # Define the three bases with their entry/exit points
        self.bases = {
            'bus': BaseConfig(
                name='Bus Depot',
                base_type='bus',
                entry_point=Position(0, 10),
                max_vehicles=15  # Can hold extra buses
            ),
            'tram': BaseConfig(
                name='Tram Depot',
                base_type='tram',
                entry_point=Position(19, 10),
                max_vehicles=10  # Can hold extra trams
            ),
            'maintenance': BaseConfig(
                name='Maintenance Base',
                base_type='maintenance',
                entry_point=Position(10, 0),
                max_vehicles=3,  # 3 maintenance vehicles
                tools=8,  # 8 tools available
                tow_hooks=2  # 2 tow hooks available
            )
        }
        
        # Track agents at each base (store agent objects, not just IDs)
        self.agents_at_base: Dict[str, Set] = {
            'bus': set(),
            'tram': set(),
            'maintenance': set()
        }
        
        # Map agent IDs to agent objects for quick lookup
        self.agent_registry: Dict[str, any] = {}
        
        # Track resource usage (maintenance base)
        self.resources_in_use = {
            'tools': 0,
            'tow_hooks': 0
        }
    
    def get_entry_point(self, base_type: str) -> Position:
        """Get the entry/exit point for a base"""
        return self.bases[base_type].entry_point
    
    def register_agent(self, agent_id: str, agent_obj: any):
        """Register an agent object for base management"""
        self.agent_registry[agent_id] = agent_obj
    
    def park_at_base(self, agent_id: str, base_type: str) -> bool:
        """Park an agent at its base (make it disappear from grid)"""
        if base_type not in self.bases:
            return False
        
        base = self.bases[base_type]
        if len(self.agents_at_base[base_type]) >= base.max_vehicles:
            print(f"⚠️ Base {base.name} is full! Cannot park {agent_id}")
            return False
        
        # Get agent object from registry
        agent_obj = self.agent_registry.get(agent_id)
        if not agent_obj:
            print(f"⚠️ {agent_id} not found in agent registry")
            return False
            
        self.agents_at_base[base_type].add(agent_obj)
        print(f"🏠 {agent_id} parked at {base.name} (object: {type(agent_obj).__name__})")
        return True
    
    def deploy_from_base(self, agent_id: str, base_type: str) -> Optional[Position]:
        """Deploy an agent from base (spawn at entry point)"""
        if base_type not in self.bases:
            return None
        
        # Find agent object by ID
        agent_obj = self.agent_registry.get(agent_id)
        if not agent_obj:
            print(f"⚠️ {agent_id} not found in agent registry")
            return None
            
        if agent_obj not in self.agents_at_base[base_type]:
            print(f"⚠️ {agent_id} is not at {self.bases[base_type].name}")
            print(f"   Agents at base: {[getattr(a, 'id', str(a)) for a in self.agents_at_base[base_type]]}")
            return None
        
        self.agents_at_base[base_type].remove(agent_obj)
        spawn_position = self.bases[base_type].entry_point
        print(f"🚀 {agent_id} deployed from {self.bases[base_type].name} at {spawn_position}")
        return spawn_position
    
    def is_at_base(self, agent_id: str, base_type: str) -> bool:
        """Check if an agent is currently at base"""
        agent_obj = self.agent_registry.get(agent_id)
        return agent_obj in self.agents_at_base.get(base_type, set()) if agent_obj else False
    
    def get_agents_at_base(self, base_type: str) -> Set[str]:
        """Get all agent IDs currently at a specific base"""
        agents = self.agents_at_base.get(base_type, set())
        return {getattr(agent, 'id', str(agent)) for agent in agents}
    
    def refuel_agent(self, agent_id: str, base_type: str) -> bool:
        """Refuel/recharge an agent at base (automatic when at_base)"""
        if self.is_at_base(agent_id, base_type):
            print(f"⛽ {agent_id} refueled at {self.bases[base_type].name}")
            return True
        return False
    
    # Maintenance resource management
    
    def request_resources(self, tools: int = 0, tow_hooks: int = 0) -> bool:
        """Request maintenance resources. Returns True if available."""
        available_tools = self.bases['maintenance'].tools - self.resources_in_use['tools']
        available_tow_hooks = self.bases['maintenance'].tow_hooks - self.resources_in_use['tow_hooks']
        
        if tools <= available_tools and tow_hooks <= available_tow_hooks:
            self.resources_in_use['tools'] += tools
            self.resources_in_use['tow_hooks'] += tow_hooks
            print(f"🔧 Resources allocated: {tools} tools, {tow_hooks} tow hooks")
            print(f"   Remaining: {available_tools - tools} tools, {available_tow_hooks - tow_hooks} tow hooks")
            return True
        
        print(f"❌ Insufficient resources! Need {tools} tools and {tow_hooks} tow hooks")
        print(f"   Available: {available_tools} tools, {available_tow_hooks} tow hooks")
        return False
    
    def release_resources(self, tools: int = 0, tow_hooks: int = 0):
        """Release maintenance resources back to the base"""
        self.resources_in_use['tools'] = max(0, self.resources_in_use['tools'] - tools)
        self.resources_in_use['tow_hooks'] = max(0, self.resources_in_use['tow_hooks'] - tow_hooks)
        print(f"✅ Resources released: {tools} tools, {tow_hooks} tow hooks")
    
    def get_available_resources(self) -> Dict[str, int]:
        """Get available maintenance resources"""
        return {
            'tools': self.bases['maintenance'].tools - self.resources_in_use['tools'],
            'tow_hooks': self.bases['maintenance'].tow_hooks - self.resources_in_use['tow_hooks'],
            'vehicles': len(self.agents_at_base['maintenance'])
        }
    
    def get_base_status(self) -> Dict:
        """Get status of all bases including parked vehicles"""
        bases_info = []
        
        # Map bases to expected format for frontend
        base_mapping = {
            'bus': ('Norte', 'bus'),
            'tram': ('Sul', 'tram'),
            'maintenance': ('Oeste', 'maintenance')
        }
        
        for base_key, (base_name, base_type) in base_mapping.items():
            base_config = self.bases[base_key]
            parked_vehicles = []
            
            # Get all vehicles parked at this base
            for agent in self.agents_at_base[base_key]:
                parked_vehicles.append({
                    'id': agent.id,
                    'type': base_type,
                    'fuel': getattr(agent, 'fuel_level', 1.0),
                    'state': getattr(agent, 'state', 'at_base')
                })
            
            base_info = {
                'name': base_name,
                'type': base_type,
                'entry_point': (base_config.entry_point.x, base_config.entry_point.y),
                'capacity': base_config.max_vehicles,
                'vehicles_at_base': len(self.agents_at_base[base_key]),
                'parked_vehicles': parked_vehicles
            }
            
            # Add resource info for maintenance base
            if base_key == 'maintenance':
                base_info['available_tools'] = base_config.tools - self.resources_in_use['tools']
                base_info['available_hooks'] = base_config.tow_hooks - self.resources_in_use['tow_hooks']
            else:
                base_info['available_tools'] = 0
                base_info['available_hooks'] = 0
            
            bases_info.append(base_info)
        
        return bases_info

