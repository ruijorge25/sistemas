"""
Contract Net Protocol implementation for agent coordination - PURE SPADE
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from spade.message import Message

from ..config.settings import MESSAGE_TYPES

class ContractNetInitiator:
    """Contract Net Protocol Initiator (e.g., Station requesting service) - PURE SPADE"""
    
    def __init__(self, agent, cfp_timeout: int = 30):
        self.agent = agent
        self.cfp_timeout = cfp_timeout
        self.active_contracts = {}  # contract_id -> contract_info
        
    async def initiate_cfp(self, task_description: Dict[str, Any], 
                          participants: List[str]) -> Optional[str]:
        """Initiate Call for Proposals using PURE SPADE messaging"""
        contract_id = f"contract_{datetime.now().timestamp()}"
        
        cfp_data = {
            'contract_id': contract_id,
            'task': task_description,
            'deadline': (datetime.now() + timedelta(seconds=self.cfp_timeout)).isoformat(),
            'initiator': str(self.agent.jid)
        }
        
        # Store contract information
        self.active_contracts[contract_id] = {
            'task': task_description,
            'participants': participants,
            'proposals': {},
            'status': 'cfp_sent',
            'deadline': datetime.now() + timedelta(seconds=self.cfp_timeout)
        }
        
        # Send CFP to all participants using SPADE send_message
        for participant in participants:
            await self.agent.send_message(
                participant,
                cfp_data,
                MESSAGE_TYPES['CONTRACT_NET_CFP']
            )
        
        print(f"📋 CFP {contract_id} sent to {len(participants)} participants")
        
        # Start proposal collection with timeout
        asyncio.create_task(self.collect_proposals(contract_id))
        
        return contract_id
    
    async def collect_proposals(self, contract_id: str):
        """Collect proposals for a contract"""
        await asyncio.sleep(self.cfp_timeout)
        
        if contract_id not in self.active_contracts:
            return
        
        contract_info = self.active_contracts[contract_id]
        proposals = contract_info['proposals']
        
        if not proposals:
            print(f"❌ No proposals received for contract {contract_id}")
            contract_info['status'] = 'failed'
            return
        
        # Evaluate proposals and select winner
        winner = await self.evaluate_proposals(proposals, contract_info['task'])
        
        if winner:
            await self.award_contract(contract_id, winner)
        else:
            print(f"❌ No suitable proposal found for contract {contract_id}")
            contract_info['status'] = 'failed'
    
    async def handle_proposal(self, msg: Message):
        """Handle incoming proposal"""
        proposal_data = json.loads(msg.body)
        contract_id = proposal_data['contract_id']
        
        if contract_id in self.active_contracts:
            contract_info = self.active_contracts[contract_id]
            contract_info['proposals'][str(msg.sender)] = proposal_data
            
            # Silently collect proposals
    
    async def evaluate_proposals(self, proposals: Dict[str, Any], 
                               task: Dict[str, Any]) -> Optional[str]:
        """Evaluate proposals and select the best one"""
        if not proposals:
            return None
        
        best_proposal = None
        best_score = -1
        
        for sender, proposal in proposals.items():
            score = await self.calculate_proposal_score(proposal, task)
            
            if score > best_score:
                best_score = score
                best_proposal = sender
        
        return best_proposal
    
    async def calculate_proposal_score(self, proposal: Dict[str, Any], 
                                     task: Dict[str, Any]) -> float:
        """Calculate score for a proposal"""
        score = 0.0
        
        # Evaluate based on different criteria
        if 'capacity' in proposal:
            # Higher capacity is better
            score += proposal['capacity'] * 0.3
        
        if 'estimated_arrival_time' in proposal and 'urgency' in task:
            # Faster arrival for urgent tasks
            arrival_time = datetime.fromisoformat(proposal['estimated_arrival_time'])
            time_until_arrival = (arrival_time - datetime.now()).total_seconds() / 60
            
            if task['urgency'] == 'high':
                score += max(0, 1.0 - time_until_arrival / 10) * 0.4  # Within 10 minutes for high urgency
            else:
                score += max(0, 1.0 - time_until_arrival / 20) * 0.4  # Within 20 minutes for normal
        
        if 'cost' in proposal:
            # Lower cost is better (normalize to 0-1 range)
            max_acceptable_cost = task.get('max_cost', 100)
            cost_score = max(0, 1.0 - proposal['cost'] / max_acceptable_cost)
            score += cost_score * 0.3
        
        return score
    
    async def award_contract(self, contract_id: str, winner: str):
        """Award contract to the winning bidder"""
        contract_info = self.active_contracts[contract_id]
        winning_proposal = contract_info['proposals'][winner]
        
        # Add initiator JID to task for contract execution
        task_with_initiator = {**contract_info['task'], 'initiator': str(self.agent.jid)}
        
        # Send acceptance to winner
        await self.agent.send_message(
            winner,
            {
                'contract_id': contract_id,
                'status': 'accepted',
                'task': task_with_initiator  # Include initiator JID
            },
            MESSAGE_TYPES['CONTRACT_NET_ACCEPT']
        )
        
        # Send rejections to other bidders
        for participant in contract_info['proposals']:
            if participant != winner:
                await self.agent.send_message(
                    participant,
                    {
                        'contract_id': contract_id,
                        'status': 'rejected'
                    },
                    MESSAGE_TYPES['CONTRACT_NET_REJECT']
                )
        
        contract_info['status'] = 'awarded'
        contract_info['winner'] = winner
        
        print(f"🏆 Contract {contract_id} awarded to {winner}")


class ContractNetParticipant:
    """Contract Net Protocol Participant (e.g., Vehicle responding to CFP)"""
    
    def __init__(self, agent):
        self.agent = agent
        self.active_bids = {}  # contract_id -> bid_info
        
    async def handle_cfp(self, msg: Message):
        """Handle Call for Proposals"""
        cfp_data = json.loads(msg.body)
        contract_id = cfp_data['contract_id']
        task = cfp_data['task']
        
        # Silently received CFP
        
        # Evaluate if we can/want to bid on this task
        can_bid = await self.can_perform_task(task)
        
        if can_bid:
            proposal = await self.create_proposal(contract_id, task)
            if proposal:
                await self.submit_proposal(str(msg.sender), proposal)
                self.active_bids[contract_id] = {
                    'proposal': proposal,
                    'initiator': str(msg.sender),
                    'status': 'submitted'
                }
        else:
            print(f"❌ Cannot bid on contract {contract_id}")
    
    async def can_perform_task(self, task: Dict[str, Any]) -> bool:
        """Determine if agent can perform the requested task"""
        # Delegate to agent if it has this method
        if hasattr(self.agent, 'can_perform_task'):
            return await self.agent.can_perform_task(task)
        return True
    
    async def create_proposal(self, contract_id: str, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a proposal for the task"""
        # Delegate to agent if it has this method
        if hasattr(self.agent, 'create_proposal'):
            return await self.agent.create_proposal(contract_id, task)
        
        # Default proposal
        return {
            'contract_id': contract_id,
            'agent_id': str(self.agent.jid),
            'estimated_arrival_time': (datetime.now() + timedelta(minutes=5)).isoformat(),
            'capacity': 30,
            'cost': 10
        }
    
    async def submit_proposal(self, initiator: str, proposal: Dict[str, Any]):
        """Submit proposal to the initiator"""
        await self.agent.send_message(
            initiator,
            proposal,
            MESSAGE_TYPES['CONTRACT_NET_PROPOSAL']
        )
        
        print(f"📤 Proposal submitted for contract {proposal.get('contract_id')} to {initiator}")
    
    async def handle_contract_result(self, msg: Message):
        """Handle contract acceptance or rejection"""
        result_data = json.loads(msg.body)
        contract_id = result_data['contract_id']
        status = result_data['status']
        
        if contract_id in self.active_bids:
            self.active_bids[contract_id]['status'] = status
            
            if status == 'accepted':
                print(f"🎉 Contract {contract_id} accepted!")
                # Start performing the task
                await self.execute_contract(contract_id, result_data.get('task', {}))
            # Silently ignore rejects - normal operation
    
    async def execute_contract(self, contract_id: str, task: Dict[str, Any]):
        """Execute the awarded contract"""
        # Delegate to agent if it has this method
        if hasattr(self.agent, 'execute_contract'):
            await self.agent.execute_contract(contract_id, task)
        else:
            print(f"🚀 Executing contract {contract_id}")
        
        # Mark contract as completed
        if contract_id in self.active_bids:
            self.active_bids[contract_id]['status'] = 'completed'