"""
Local Message Bus for agent communication without XMPP
Simulates SPADE ACL message passing in local mode
"""
import asyncio
from typing import Dict, List, Callable, Any
import json
from datetime import datetime
from dataclasses import dataclass, field

@dataclass
class LocalMessage:
    """Local representation of SPADE Message"""
    sender: str
    to: str
    body: str
    metadata: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value"""
        return self.metadata.get(key, default)
    
    def set_metadata(self, key: str, value: str):
        """Set metadata value"""
        self.metadata[key] = value


class LocalMessageBus:
    """
    Singleton message bus for local agent communication
    Routes messages between agents without XMPP server
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalMessageBus, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.message_queues: Dict[str, asyncio.Queue] = {}
            self.agent_callbacks: Dict[str, List[Callable]] = {}
            self.message_log: List[LocalMessage] = []
            self._initialized = True
            print("📬 Local Message Bus initialized")
    
    def register_agent(self, jid: str):
        """Register an agent with the message bus"""
        if jid not in self.message_queues:
            self.message_queues[jid] = asyncio.Queue()
            self.agent_callbacks[jid] = []
            print(f"📝 Agent {jid} registered with message bus")
    
    async def send_message(self, sender_jid: str, to_jid: str, body: str, metadata: Dict[str, str] = None):
        """Send a message from one agent to another"""
        if to_jid not in self.message_queues:
            print(f"⚠️ Warning: Agent {to_jid} not registered with message bus")
            return
        
        msg = LocalMessage(
            sender=sender_jid,
            to=to_jid,
            body=body,
            metadata=metadata or {}
        )
        
        # Log message
        self.message_log.append(msg)
        
        # Put in recipient's queue
        await self.message_queues[to_jid].put(msg)
        
        # Call callbacks if registered
        for callback in self.agent_callbacks.get(to_jid, []):
            asyncio.create_task(callback(msg))
        
        print(f"📨 Message routed: {sender_jid} → {to_jid} [Type: {metadata.get('type', 'unknown')}]")
    
    async def receive_message(self, jid: str, timeout: float = 1.0) -> LocalMessage:
        """Receive a message for an agent (non-blocking with timeout)"""
        if jid not in self.message_queues:
            return None
        
        try:
            msg = await asyncio.wait_for(self.message_queues[jid].get(), timeout=timeout)
            return msg
        except asyncio.TimeoutError:
            return None
    
    def register_callback(self, jid: str, callback: Callable):
        """Register a callback for when messages arrive"""
        if jid not in self.agent_callbacks:
            self.agent_callbacks[jid] = []
        self.agent_callbacks[jid].append(callback)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get message bus statistics"""
        return {
            'total_agents': len(self.message_queues),
            'total_messages': len(self.message_log),
            'queue_sizes': {jid: queue.qsize() for jid, queue in self.message_queues.items()}
        }
    
    def clear(self):
        """Clear all queues and logs (for testing)"""
        self.message_queues.clear()
        self.agent_callbacks.clear()
        self.message_log.clear()


# Global singleton instance
message_bus = LocalMessageBus()
