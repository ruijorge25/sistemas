# 🚌 Sistema Multi-Agente Descentralizado de Transportes Públicos

## 📋 Índice
1. [Visão Geral](#visão-geral)
2. [Arquitetura do Sistema](#arquitetura)
3. [Agentes Implementados](#agentes)
4. [Machine Learning](#machine-learning)
5. [Contract Net Protocol FIPA](#cnp)
6. [Cooperação entre Veículos](#cooperacao)
7. [Dashboard Web](#dashboard)
8. [Estrutura de Ficheiros](#estrutura)
9. [Como Executar](#executar)

---

## 🎯 Visão Geral

Sistema completo de gestão descentralizada de transportes públicos usando **SPADE** (Smart Python Agent Development Environment) com 4 tipos de agentes autónomos que comunicam via XMPP.

### **Objetivos Cumpridos:**
- ✅ Sistema multi-agente descentralizado com SPADE
- ✅ 4 tipos de agentes (Veículos, Estações, Passageiros, Manutenção)
- ✅ Machine Learning integrado (Q-Learning, Demand Prediction)
- ✅ Contract Net Protocol FIPA para negociação
- ✅ Cooperação veículo-a-veículo
- ✅ Dashboard web em tempo real
- ✅ Otimização dinâmica de rotas
- ✅ Métricas de desempenho completas

### **Estatísticas do Projeto:**
- **Linhas de Código Python:** ~5,500+
- **Ficheiros Python:** 24
- **Agentes Implementados:** 4 tipos
- **Behaviours SPADE:** 20+
- **Protocolos de Comunicação:** CNP FIPA + Mensagens Diretas
- **Algoritmos ML:** 4 (DemandPredictor, QLearning, PatternRecognizer, ReinforcementLearner)

---

## 🏗️ Arquitetura do Sistema

### **Tecnologias Utilizadas:**
```
SPADE 3.2.0       → Framework multi-agente (XMPP)
Python 3.12       → Linguagem principal
Aiohttp           → Servidor web assíncrono
Chart.js 4.4.0    → Gráficos em tempo real
HTML5/CSS3/JS     → Dashboard interativo
NumPy             → Computação científica
```

### **Padrão de Comunicação:**
```
┌─────────────┐
│   XMPP      │  ← Protocolo de comunicação (ejabberd/prosody)
│   Server    │
└──────┬──────┘
       │
       ├──────► StationAgent@localhost
       ├──────► VehicleAgent@localhost
       ├──────► PassengerAgent@localhost
       └──────► MaintenanceAgent@localhost
```

### **Fluxo de Decisão:**
1. **Passageiro** chega à estação → Entra na fila
2. **Estação** detecta procura alta → Inicia CNP para pedir veículos
3. **Veículos** avaliam proposta → Enviam bids competitivos
4. **Estação** escolhe melhor → Atribui contrato
5. **Veículo** executa → Recolhe passageiros
6. **Manutenção** monitoriza → Repara avarias

---

##  Agentes Implementados

### **1. StationAgent** (Esta��es de Autocarros/El�tricos)

**Ficheiro:** `src/agents/station_agent.py` (373 linhas)

#### **Responsabilidades:**
- Gerir fila de passageiros (deque com max 100)
- Prever procura usando Machine Learning
- Pedir ve�culos quando necess�rio (CNP)
- Monitorizar ve�culos dispon�veis
- Partilhar previs�es com esta��es vizinhas

#### **Attributes Principais:**
```python
self.station_id              # ID �nico da esta��o
self.position                # Posi��o no grid (x, y)
self.station_type            # 'bus', 'tram' ou 'mixed'
self.passenger_queue         # Fila de passageiros (deque)
self.current_demand          # Procura atual
self.predicted_demand        # Previs�o ML
self.demand_predictor        # DemandPredictor (ML)
self.pattern_recognizer      # PatternRecognizer (ML)
self.cnp_initiator          # Contract Net Protocol
```

#### **Behaviours (5):**
1. **PassengerArrivalSimulation** - Simula chegada de passageiros (3-7s)
2. **VehicleMonitoring** - Monitoriza ve�culos pr�ximos (10s)
3. **DemandForecasting** - Atualiza previs�es ML (30s)
4. **ServiceRequestManagement** - Verifica necessidade de ve�culos (5s)
5. **ContractNetHandler** - Trata mensagens CNP (PROPOSE, INFORM)

#### **L�gica de Pedido de Ve�culos (CNP):**
```python
async def request_additional_service(self):
    # S� pede se fila > threshold (20 passageiros)
    if len(self.passenger_queue) > self.overcrowding_threshold:
        
        # Cria task description
        task = {
            'station_id': self.station_id,
            'position': {'x': self.position.x, 'y': self.position.y},
            'demand_level': len(self.passenger_queue),
            'urgency': 'high' if queue > 30 else 'medium',
            'required_capacity': min(len(queue), 50)
        }
        
        # Inicia CNP com ve�culos pr�ximos
        contract_id = await self.cnp_initiator.initiate_cfp(
            task, 
            nearby_vehicles
        )
```

#### **Machine Learning:**
- **DemandPredictor:** Aprende padr�es de procura por hora/dia
- **PatternRecognizer:** Detecta rush hours e anomalias
- Previs�es usadas para otimizar pedidos de ve�culos

---

### **2. VehicleAgent** (Autocarros e El�tricos)

**Ficheiro:** `src/agents/vehicle_agent.py` (418 linhas)

#### **Responsabilidades:**
- Mover entre esta��es na rota atribu�da
- Recolher e transportar passageiros
- Responder a CNP de esta��es
- Negociar coopera��o com outros ve�culos
- Pedir manuten��o quando avariado
- Otimizar rotas dinamicamente (Q-Learning)

#### **Attributes Principais:**
```python
self.vehicle_id              # ID �nico
self.vehicle_type            # 'bus' ou 'tram'
self.assigned_route          # Rota atribu�da
self.current_position        # Posi��o atual
self.passengers              # Lista de PassengerInfo
self.capacity                # 40 passageiros
self.fuel_level              # 0-100
self.is_broken               # Estado de avaria
self.q_learner               # QLearningRouter (ML)
self.cnp_participant         # Contract Net Protocol
```

#### **Behaviours (7):**
1. **MovementBehaviour** - Move para pr�xima esta��o (5s)
2. **PassengerManagement** - Embarca/desembarca passageiros (1s)
3. **CapacityNegotiation** - Negocia capacidade com esta��es (1s)
4. **MaintenanceMonitoring** - Verifica sa�de do ve�culo (10s)
5. **RouteAdaptation** - Adapta rota dinamicamente (20s)
6. **ContractNetHandler** - Trata CFP, ACCEPT, REJECT (1s)
7. **CooperationHandler** - Coopera com outros ve�culos

#### **Q-Learning para Rotas:**
```python
# Estado: (posi��o, combust�vel, passageiros)
state = self.q_learner.get_state(
    self.current_position,
    self.fuel_level,
    len(self.passengers)
)

# Escolhe pr�xima esta��o (epsilon-greedy)
next_station_idx = self.q_learner.choose_action(state)

# Recebe reward baseado em:
# - Passageiros entregues no destino
# - Tempo de espera
# - Utiliza��o de capacidade
reward = calculate_reward(...)

# Atualiza Q-table
self.q_learner.update(state, action, reward, next_state)
```

#### **Contract Net Protocol (Participant):**
```python
async def can_perform_task(self, task):
    # Verifica se pode executar
    if self.is_broken or self.fuel_level < 20:
        return False
    
    available_capacity = self.capacity - len(self.passengers)
    if available_capacity < task['required_capacity']:
        return False
    
    distance = calculate_distance(self.position, task['position'])
    if distance > 20:
        return False
    
    return True

async def create_proposal(self, contract_id, task):
    # Cria proposta competitiva
    distance = calculate_distance(...)
    travel_time = (distance * 0.5) / self.speed_modifier
    
    return {
        'contract_id': contract_id,
        'estimated_arrival_time': now + timedelta(minutes=travel_time),
        'capacity': self.capacity - len(self.passengers),
        'cost': distance * 2 * (1.5 if urgent else 1.0),
        'fuel_level': self.fuel_level
    }
```

---

### **3. PassengerAgent** (Passageiros Individuais)

**Ficheiro:** `src/agents/passenger_agent.py` (331 linhas)

#### **Responsabilidades:**
- Esperar na esta��o
- Procurar ve�culos dispon�veis
- Negociar viagem (pode usar CNP)
- Viajar at� destino
- Desistir se espera for excessiva

#### **Attributes Principais:**
```python
self.passenger_id            # ID �nico
self.origin                  # Esta��o de origem
self.destination             # Esta��o de destino
self.state                   # 'waiting', 'traveling', 'arrived', 'gave_up'
self.patience_time           # 15 minutos (configur�vel)
self.vehicle_proposals       # Propostas recebidas
self.cnp_initiator          # Para procurar ve�culos
```

#### **Behaviours (4):**
1. **RouteDiscovery** - Descobre rotas poss�veis
2. **VehicleNegotiation** - Recebe ofertas de ve�culos (1s)
3. **PatienceMonitoring** - Verifica timeout de espera (5s)
4. **TravelMonitoring** - Monitoriza viagem em curso

#### **Estados e Transi��es:**
```
WAITING  TRAVELING (embarcou em ve�culo)
         GAVE_UP (esperou > patience_time)

TRAVELING  ARRIVED (chegou ao destino)
           WAITING (ve�culo avariou)
```

---

### **4. MaintenanceAgent** (Equipas de Manuten��o)

**Ficheiro:** `src/agents/maintenance_agent.py` (255 linhas)

#### **Responsabilidades:**
- Monitorizar pedidos de repara��o
- Priorizar jobs (urg�ncia, proximidade)
- Mover at� ve�culo avariado
- Reparar ve�culo (5 min simulados)
- Gerir m�ltiplos jobs em paralelo

#### **Attributes Principais:**
```python
self.crew_id                 # ID da equipa
self.current_position        # Posi��o no grid
self.is_busy                 # A reparar ou n�o
self.repair_queue            # Fila de jobs priorizados
self.jobs_completed          # Contador de repara��es
self.available_tools         # ['basic', 'engine', 'electrical']
```

#### **Behaviours (3):**
1. **BreakdownResponseBehaviour** - Recebe alertas de avarias (1s)
2. **RepairExecution** - Executa repara��es (5s)
3. **JobPrioritization** - Reordena fila por urg�ncia (10s)

#### **L�gica de Prioriza��o:**
```python
def prioritize_jobs(self):
    # Score = urg�ncia + proximidade + tempo_espera
    for job in self.repair_queue:
        urgency_score = 10 if job['vehicle_type'] == 'tram' else 5
        
        distance = calculate_distance(self.position, job['position'])
        proximity_score = max(0, 10 - distance)
        
        wait_time = (now - job['timestamp']).seconds / 60
        wait_score = min(wait_time, 10)
        
        job['priority'] = urgency_score + proximity_score + wait_score
    
    self.repair_queue.sort(key=lambda x: x['priority'], reverse=True)
```

---

##  Machine Learning

### **Ficheiro:** `src/ml/learning.py` (389 linhas)

### **1. DemandPredictor** - Previs�o de Procura

#### **Algoritmo:**
Previs�o multi-sinal com pesos adaptativos.

```python
class DemandPredictor:
    def predict(self, hour, day_of_week):
        # 4 sinais de previs�o
        hour_pattern = self.hourly_patterns.get(hour, 0)      # 40%
        day_pattern = self.daily_patterns.get(day, 0)          # 20%
        recent_trend = mean(self.recent_observations[-10:])    # 30%
        historical_avg = mean(all_observations)                 # 10%
        
        prediction = (
            0.4 * hour_pattern +
            0.3 * recent_trend +
            0.2 * day_pattern +
            0.1 * historical_avg
        )
        
        # Confian�a baseada em quantidade de dados
        confidence = min(len(observations) / 100, 1.0)
        
        return prediction, confidence
```

#### **Aprendizagem:**
- Observa procura real a cada 30s
- Atualiza padr�es por hora (24 bins)
- Atualiza padr�es por dia (7 dias semana)
- Mant�m hist�rico de 200 observa��es
- Calcula m�dia e desvio padr�o

---

### **2. QLearningRouter** - Rotas Inteligentes

#### **Algoritmo:**
Q-Learning com epsilon-greedy exploration.

```python
class QLearningRouter:
    def __init__(self, num_stations, learning_rate=0.1, discount=0.9, epsilon=0.2):
        # Q-table: estados  a��es  valor esperado
        self.q_table = {}
        self.alpha = learning_rate    # Taxa de aprendizagem
        self.gamma = discount          # Fator de desconto
        self.epsilon = epsilon         # Explora��o vs explora��o
        self.min_epsilon = 0.05
        self.epsilon_decay = 0.995
    
    def choose_action(self, state):
        if random() < self.epsilon:
            # EXPLORA��O: Tenta a��o aleat�ria
            return random.randint(0, self.num_stations - 1)
        else:
            # EXPLORA��O: Usa conhecimento (melhor Q-value)
            return self.get_best_action(state)
    
    def update(self, state, action, reward, next_state):
        # Q-learning update rule
        old_q = self.get_q_value(state, action)
        next_max_q = max(self.get_all_q_values(next_state))
        
        new_q = old_q + self.alpha * (reward + self.gamma * next_max_q - old_q)
        
        self.set_q_value(state, action, new_q)
        
        # Decay epsilon (menos explora��o com tempo)
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)
```

#### **Estado:**
```python
state = (
    current_station_idx,
    fuel_bucket,          # 0: <20, 1: 20-50, 2: 50-80, 3: >80
    passenger_bucket      # 0: <10, 1: 10-25, 2: 25-35, 3: >35
)
```

#### **Reward:**
```python
reward = 0
reward += passengers_delivered * 10          # +10 por passageiro entregue
reward -= waiting_time_minutes * 0.5         # -0.5 por minuto de espera
reward += (capacity_used / capacity) * 5     # +5 se bem utilizado
reward -= fuel_consumption * 0.1             # -0.1 por unidade combust�vel
```

---

### **3. PatternRecognizer** - Dete��o de Padr�es

#### **Fun��es:**

```python
class PatternRecognizer:
    def detect_rush_hour(self, demand_history):
        # Rush hour se procura > 1.5x m�dia
        avg = mean(demand_history)
        current = demand_history[-1]
        return current > avg * 1.5
    
    def detect_anomaly(self, current_demand, history):
        # Anomalia se procura > m�dia + 2s
        avg = mean(history)
        std = stdev(history)
        return current_demand > avg + 2 * std
    
    def identify_peak_hours(self, hourly_data):
        # Top 3 horas com mais procura
        sorted_hours = sorted(hourly_data.items(), key=lambda x: x[1], reverse=True)
        return [hour for hour, _ in sorted_hours[:3]]
```

---

### **4. ReinforcementLearner** - Multi-Armed Bandit

#### **Algoritmo:**
Incremental average para estimar valor de a��es.

```python
class ReinforcementLearner:
    def select_action(self):
        # Seleciona a��o com maior valor estimado
        return max(self.action_values, key=self.action_values.get)
    
    def update_action_value(self, action, reward):
        # Atualiza��o incremental da m�dia
        n = self.action_counts[action]
        old_value = self.action_values[action]
        
        # Nova m�dia: old + (1/n) * (reward - old)
        new_value = old_value + (1/n) * (reward - old_value)
        
        self.action_values[action] = new_value
        self.action_counts[action] += 1
```

---

##  Contract Net Protocol FIPA

### **Ficheiro:** `src/protocols/contract_net.py` (251 linhas)

Sistema completo de negocia��o descentralizada seguindo o padr�o **FIPA Contract Net Interaction Protocol**.

### **Fluxo do Protocolo:**

```
1. CFP (Call for Proposals)
   Station detecta queue > 20
   
   Envia CFP para nearby vehicles
   {contract_id, task, deadline, urgency}

2. PROPOSE
   Vehicles avaliam can_perform_task()
   
   Criam propostas competitivas
   {arrival_time, capacity, cost, fuel}

3. EVALUATE
   Station aguarda timeout (10s)
   
   Calcula score para cada proposta
   score = 0.3*capacity + 0.4*time + 0.3*cost

4. ACCEPT / REJECT
   Station escolhe vencedor
   
   ACCEPT ao melhor, REJECT aos outros

5. EXECUTE
   Vehicle vencedor executa contrato
   
   Move para station, recolhe passageiros
   
   INFORM quando completo
```

### **ContractNetInitiator** (usado por Station e Passenger)

```python
class ContractNetInitiator:
    def __init__(self, agent, cfp_timeout=10):
        self.agent = agent
        self.cfp_timeout = cfp_timeout
        self.active_contracts = {}
    
    async def initiate_cfp(self, task_description, participants):
        # Cria contract_id �nico
        contract_id = f"contract_{timestamp()}"
        
        # Envia CFP para todos os participantes
        for participant in participants:
            await self.agent.send_message(
                participant,
                {
                    'contract_id': contract_id,
                    'task': task_description,
                    'deadline': now + timedelta(seconds=self.cfp_timeout)
                },
                MESSAGE_TYPES['CONTRACT_NET_CFP']
            )
        
        # Inicia coleta de propostas (async)
        asyncio.create_task(self.collect_proposals(contract_id))
        
        return contract_id
    
    async def collect_proposals(self, contract_id):
        await asyncio.sleep(self.cfp_timeout)
        
        proposals = self.active_contracts[contract_id]['proposals']
        
        if not proposals:
            return  # Nenhuma proposta
        
        # Avalia e escolhe vencedor
        winner = await self.evaluate_proposals(proposals, task)
        await self.award_contract(contract_id, winner)
    
    async def evaluate_proposals(self, proposals, task):
        best_score = -1
        best_proposal = None
        
        for sender, proposal in proposals.items():
            score = 0.0
            
            # Capacidade (30%)
            score += proposal['capacity'] * 0.3
            
            # Tempo de chegada (40%)
            arrival = datetime.fromisoformat(proposal['estimated_arrival_time'])
            time_score = max(0, 1.0 - (arrival - now).seconds / 600)
            score += time_score * 0.4
            
            # Custo (30%)
            cost_score = max(0, 1.0 - proposal['cost'] / task['max_cost'])
            score += cost_score * 0.3
            
            if score > best_score:
                best_score = score
                best_proposal = sender
        
        return best_proposal
```

### **ContractNetParticipant** (usado por Vehicle)

```python
class ContractNetParticipant:
    def __init__(self, agent):
        self.agent = agent
        self.active_bids = {}
    
    async def handle_cfp(self, msg):
        cfp_data = json.loads(msg.body)
        contract_id = cfp_data['contract_id']
        task = cfp_data['task']
        
        # Avalia se pode fazer (delega para agent)
        can_bid = await self.can_perform_task(task)
        
        if can_bid:
            # Cria proposta (delega para agent)
            proposal = await self.create_proposal(contract_id, task)
            
            if proposal:
                # Envia proposta
                await self.submit_proposal(msg.sender, proposal)
                self.active_bids[contract_id] = {
                    'proposal': proposal,
                    'status': 'submitted'
                }
    
    async def can_perform_task(self, task):
        # Delega para agent (VehicleAgent tem implementa��o)
        if hasattr(self.agent, 'can_perform_task'):
            return await self.agent.can_perform_task(task)
        return True
    
    async def handle_contract_result(self, msg):
        result = json.loads(msg.body)
        contract_id = result['contract_id']
        status = result['status']
        
        if status == 'accepted':
            # Executa contrato (delega para agent)
            await self.execute_contract(contract_id, result['task'])
        else:
            # Rejeitado - nada a fazer
            pass
```

### **Tipos de Mensagens CNP:**

```python
MESSAGE_TYPES = {
    'CONTRACT_NET_CFP':      'cfp',      # Call for Proposals
    'CONTRACT_NET_PROPOSE':  'propose',  # Bidding
    'CONTRACT_NET_ACCEPT':   'accept',   # Winner notification
    'CONTRACT_NET_REJECT':   'reject',   # Loser notification
    'CONTRACT_NET_INFORM':   'inform'    # Execution complete
}
```

---

##  Coopera��o entre Ve�culos

### **Ficheiro:** `src/agents/cooperation.py` (246 linhas)

Sistema de coordena��o ve�culo-a-ve�culo para evitar sobreposi��o e otimizar cobertura.

### **VehicleCoordinator**

```python
class VehicleCoordinator:
    def __init__(self):
        self.vehicle_intentions = {}     # vehicle_id  intention_info
        self.vehicle_positions = {}       # vehicle_id  position
        self.cooperation_events = []      # Log de coopera��es
    
    async def announce_intention(self, vehicle_id, target_station, eta):
        # Verifica se station j� tem ve�culos a caminho
        existing = self.get_vehicles_going_to(target_station)
        
        if not existing:
            return (True, "first_responder", None)
        
        # Compara ETAs
        my_eta = eta
        their_eta = min(v['eta'] for v in existing)
        
        if my_eta < their_eta:
            return (True, "faster_arrival", None)
        else:
            # Sugere esta��o alternativa
            alternative = self.find_alternative_station(target_station)
            return (False, "already_covered", alternative)
    
    async def form_convoy(self, vehicle_id, target_station):
        # Encontra ve�culos pr�ximos indo para mesmo destino
        nearby = []
        my_pos = self.vehicle_positions[vehicle_id]
        
        for other_id, intention in self.vehicle_intentions.items():
            if intention['target'] == target_station and other_id != vehicle_id:
                other_pos = self.vehicle_positions[other_id]
                distance = calculate_distance(my_pos, other_pos)
                
                if distance <= 5:  # Raio de 5 c�lulas
                    nearby.append(other_id)
        
        if nearby:
            convoy_id = f"convoy_{timestamp()}"
            self.cooperation_events.append({
                'type': 'convoy_formed',
                'leader': vehicle_id,
                'members': nearby,
                'target': target_station
            })
            return convoy_id, nearby
        
        return None, []
    
    async def negotiate_load_balancing(self, station_id, vehicles):
        # Distribui passageiros por m�ltiplos ve�culos
        total_capacity = sum(v['available_capacity'] for v in vehicles)
        station_demand = self.get_station_demand(station_id)
        
        distribution = {}
        for vehicle in vehicles:
            share = (vehicle['available_capacity'] / total_capacity)
            distribution[vehicle['id']] = int(station_demand * share)
        
        return distribution
```

### **CooperativeMessageProtocol**

7 tipos de mensagens cooperativas:

```python
1. INTENTION_ANNOUNCE
   {vehicle_id, target_station, eta, current_position}

2. CONVOY_INVITE
   {initiator_id, target_station, convoy_id}

3. CONVOY_ACCEPT
   {vehicle_id, convoy_id}

4. LOAD_BALANCE
   {station_id, vehicles_involved, distribution}

5. POSITION_UPDATE
   {vehicle_id, position, timestamp}

6. HELP_REQUEST
   {vehicle_id, reason, position}

7. HELP_RESPONSE
   {responder_id, help_type, eta}
```

---

##  Dashboard Web

### **Ficheiro:** `main.py` (SimpleDashboardServer integrado)

Dashboard em tempo real com Chart.js e atualiza��es ass�ncronas.

### **Servidor Aiohttp:**

```python
class SimpleDashboardServer:
    def __init__(self, city, port=8080):
        self.city = city
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/api/status', self.get_status)
        self.app.router.add_get('/api/vehicles', self.get_vehicles)
        self.app.router.add_get('/api/stations', self.get_stations)
        self.app.router.add_get('/api/metrics', self.get_metrics)
    
    async def index(self, request):
        # Serve dashboard_advanced.html
        with open('src/visualization/templates/dashboard_advanced.html') as f:
            return web.Response(text=f.read(), content_type='text/html')
```

### **Dashboard:** `src/visualization/templates/dashboard_advanced.html` (825 linhas)

#### **Caracter�sticas:**
-  7 m�tricas em tempo real
-  2 gr�ficos Chart.js (line + doughnut)
-  Heatmap 2020 da cidade
-  Lista de ve�culos ativos
-  Lista de esta��es com filas
-  Eventos de coopera��o
-  Estat�sticas ML
-  Updates a cada 2 segundos

#### **M�tricas Exibidas:**

```javascript
1. Passageiros Esperando
   - Total em todas as esta��es
   - Trend:  /  / 

2. Ve�culos Ativos
   - Total n�o avariados
   - % da frota

3. Taxa de Pontualidade
   - % chegadas a tempo
   - Target: >85%

4. Utiliza��o da Frota
   - M�dia de ocupa��o
   - Target: 60-80%

5. Tempo M�dio de Espera
   - Minutos m�dios
   - Target: <10 min

6. Coopera��es Ativas
   - Convoys + load balancing
   - Count atual

7. Aprendizagem ML
   - Q-learning epsilon
   - Previs�es ativas
```

#### **Gr�ficos:**

```javascript
// Gr�fico de Performance (Line)
{
    datasets: [
        {label: 'Utiliza��o Frota', color: '#667eea'},
        {label: 'Pontualidade', color: '#f093fb'}
    ],
    history: 20 pontos
}

// Gr�fico de Frota (Doughnut)
{
    data: [ativos, avariados, em_manuten��o],
    colors: ['#10b981', '#ef4444', '#f59e0b']
}
```

#### **Heatmap da Cidade:**

```javascript
// Grid 2020 com overlay de ve�culos e esta��es
for (let y = 0; y < 20; y++) {
    for (let x = 0; x < 20; x++) {
        cell.style.background = 
gba(79, 70, 229, )
    }
}

// Sobreposi��o de ve�culos (/)
vehicles.forEach(v => {
    cell[v.y][v.x].innerHTML = v.type === 'bus' ? '' : ''
})

// Sobreposi��o de esta��es ()
stations.forEach(s => {
    cell[s.y][s.x].innerHTML = ''
    cell[s.y][s.x].title = Queue: 
})
```

---

##  Estrutura Completa de Ficheiros

```
sistemas/

 main.py                         # Entry point principal (dashboard integrado)
 demo.py                         # Demo sem XMPP (mock agents)
 requirements.txt                # Depend�ncias Python
 test_setup.py                   # Testes de setup
 test_scenarios.py               # Testes de cen�rios

 src/
    __init__.py
   
    agents/                     #  Agentes SPADE
       __init__.py
       base_agent.py           # Classe base (73 linhas)
       station_agent.py        # Esta��es (373 linhas)  CNP
       vehicle_agent.py        # Ve�culos (418 linhas)  CNP + ML
       passenger_agent.py      # Passageiros (331 linhas)  CNP
       maintenance_agent.py    # Manuten��o (255 linhas)
       cooperation.py          # Coopera��o V2V (246 linhas)
   
    protocols/                  #  Protocolos FIPA
       __init__.py
       contract_net.py         # CNP completo (251 linhas)
   
    ml/                         #  Machine Learning
       __init__.py
       learning.py             # 4 algoritmos ML (389 linhas)
           DemandPredictor
           QLearningRouter
           PatternRecognizer
           ReinforcementLearner
   
    environment/                #  Ambiente
       __init__.py
       city.py                 # Grid, rotas, posi��es (287 linhas)
       route_optimizer.py     # Otimiza��o rotas (245 linhas)
   
    config/                     #  Configura��o
       __init__.py
       settings.py             # Constantes (75 linhas)
           SIMULATION_CONFIG
           MESSAGE_TYPES
           METRICS
   
    metrics/                    #  M�tricas
       __init__.py
       collector.py            # Coleta e agrega��o
   
    simulation/                 #  Coordena��o
       __init__.py
       coordinator.py          # SimulationCoordinator (198 linhas)
   
    visualization/              #  Dashboard
        __init__.py
        console.py              # Output ASCII
        dashboard.py            # Servidor web (143 linhas)
        templates/
            dashboard_advanced.html  # UI completo (825 linhas)

 spade_venv/                     # Virtual environment
```

### **Total de C�digo:**
- **Ficheiros Python:** 24
- **Linhas de C�digo:** ~5,500+
- **Ficheiros HTML/CSS/JS:** 1 (825 linhas)
- **Total Geral:** ~6,325 linhas

---

##  Como Executar

### **1. Instala��o**

```powershell
# Clone o reposit�rio
cd "c:\Users\Rui Almeida\Desktop\Uni\sistemas"

# Cria ambiente virtual
python -m venv spade_venv

# Ativa ambiente
.\spade_venv\Scripts\Activate.ps1

# Instala depend�ncias
pip install -r requirements.txt
```

### **2. Depend�ncias Principais**

```
spade==3.2.0           # Framework multi-agente
aiohttp==3.10.4        # Servidor web ass�ncrono
numpy                  # Computa��o cient�fica
matplotlib             # Visualiza��o (opcional)
asyncio-mqtt           # MQTT para comunica��o
```

### **3. Servidor XMPP (Necess�rio)**

O SPADE requer um servidor XMPP. Op��es:

**Op��o A: ejabberd local**
```powershell
# Instalar ejabberd
# Configurar dom�nio: localhost
# Criar contas para agentes
```

**Op��o B: Prosody local**
```powershell
# Instalar Prosody
# Permitir registo local
```

**Op��o C: Demo sem XMPP**
```powershell
# Executa vers�o simplificada sem SPADE
python demo.py
```

### **4. Executar Sistema Completo**

```powershell
# Sistema completo com dashboard
python main.py

# Dashboard dispon�vel em:
# http://localhost:8080
```

### **5. Configura��o**

Editar `src/config/settings.py`:

```python
SIMULATION_CONFIG = {
    'city': {
        'grid_size': (20, 20),        # Tamanho do grid
        'num_stations': 15,            # N�mero de esta��es
        'num_vehicles': 10,            # N�mero de ve�culos
        'num_passengers': 50,          # Passageiros inicial
        'num_maintenance_crews': 3     # Equipas manuten��o
    },
    'vehicle': {
        'capacity': 40,                # Capacidade ve�culo
        'breakdown_probability': 0.001 # Prob. avaria por ciclo
    },
    'passenger': {
        'patience_time': 15,           # Minutos max espera
        'arrival_rate': 0.3            # Taxa chegada/ciclo
    }
}
```

---

##  M�tricas e Desempenho

### **M�tricas Principais:**

```python
METRICS = [
    'average_waiting_time',           # Tempo m�dio espera (min)
    'fleet_utilization',              # % ocupa��o frota
    'on_time_performance',            # % chegadas pontuais
    'passenger_satisfaction',         # Score satisfa��o
    'collaboration_effectiveness',    # Sucesso coopera��o
    'fuel_efficiency',                # Consumo combust�vel
    'breakdown_response_time'         # Tempo resposta avarias
]
```

### **Targets de Desempenho:**

| M�trica | Target | Descri��o |
|---------|--------|-----------|
| Tempo Espera | < 10 min | M�dia de espera aceit�vel |
| Utiliza��o Frota | 60-80% | Nem vazio nem lotado |
| Pontualidade | > 85% | Maioria chega a tempo |
| Satisfa��o | > 7/10 | Passageiros satisfeitos |
| Coopera��o | > 70% | Maioria coopera��es bem-sucedidas |
| Resposta Avarias | < 5 min | Manuten��o r�pida |

### **Coleta de M�tricas:**

```python
# Cada agente regista m�tricas
self.log_metric('waiting_time', time_in_seconds)
self.log_metric('utilization', passengers / capacity)

# Coordinator agrega
total_waiting = sum(agent.metrics['waiting_time'] for agent in stations)
average = total_waiting / len(stations)
```

---

##  Funcionalidades Implementadas

###  **Requisitos Base (100%)**
- [x] Sistema multi-agente descentralizado
- [x] SPADE 3.2.0 com comunica��o XMPP
- [x] 4 tipos de agentes aut�nomos
- [x] Comunica��o agente-a-agente
- [x] Behaviours ass�ncronos
- [x] Grid 2020 para ambiente
- [x] Gest�o de rotas e posi��es

###  **Machine Learning (Avan�ado)**
- [x] DemandPredictor com multi-signal
- [x] Q-Learning para rotas inteligentes
- [x] Pattern Recognition (rush hour, anomalias)
- [x] Reinforcement Learning gen�rico
- [x] Epsilon-greedy exploration
- [x] Previs�es integradas nos agentes

###  **Contract Net Protocol FIPA (Avan�ado)**
- [x] CNP completo seguindo padr�o FIPA
- [x] CFP  PROPOSE  EVALUATE  ACCEPT/REJECT  EXECUTE
- [x] Avalia��o objetiva com scoring
- [x] Timeout handling
- [x] Negocia��o competitiva
- [x] Integrado em Station e Vehicle

###  **Coopera��o Ve�culo-a-Ve�culo (Avan�ado)**
- [x] An�ncio de inten��es
- [x] Forma��o de convoys
- [x] Load balancing entre ve�culos
- [x] Position tracking
- [x] 7 tipos de mensagens cooperativas
- [x] VehicleCoordinator central

###  **Dashboard Web (Avan�ado)**
- [x] Interface em tempo real
- [x] 7 m�tricas din�micas
- [x] 2 gr�ficos Chart.js
- [x] Heatmap 2020
- [x] Lista ve�culos/esta��es
- [x] Eventos de coopera��o
- [x] Atualiza��o a cada 2s

###  **Otimiza��es**
- [x] Rotas din�micas (DynamicRouteAdapter)
- [x] Prioriza��o de jobs de manuten��o
- [x] Gest�o de combust�vel
- [x] Detec��o de avarias
- [x] Timeout de paci�ncia de passageiros

---

##  Conceitos Acad�micos Aplicados

### **1. Sistemas Multi-Agente**
- Autonomia: Cada agente decide independentemente
- Reatividade: Responde a mudan�as no ambiente
- Proatividade: Toma iniciativa (CNP, coopera��o)
- Habilidade social: Comunica via XMPP/FIPA

### **2. FIPA Standards**
- Contract Net Protocol
- ACL (Agent Communication Language)
- Mensagens estruturadas (performatives)
- Ontologias e sem�ntica

### **3. Aprendizagem por Refor�o**
- Q-Learning: V(s,a) = V(s,a) + a[r + ? max V(s',a') - V(s,a)]
- Exploration vs Exploitation
- Epsilon-greedy policy
- Reward shaping

### **4. Coordena��o Descentralizada**
- Sem controlo central
- Emergent behavior
- Negocia��o peer-to-peer
- Consensus atrav�s de protocolos

### **5. Otimiza��o Distribu�da**
- Rotas din�micas
- Load balancing
- Resource allocation
- Pareto efficiency

---

##  Testes

### **test_setup.py**
Testa imports e configura��o inicial:
```python
- Config module
- Environment module
- Agent modules
- Protocol modules
```

### **test_scenarios.py** (340 linhas)
Cen�rios de teste autom�ticos:
```python
1. Normal Operations      # Opera��o padr�o
2. Rush Hour             # Procura alta
3. Multiple Breakdowns   # M�ltiplas avarias
4. High Demand Event     # Evento especial
5. Traffic Congestion    # Congestionamento
```

### **Executar Testes:**
```powershell
# Testes de setup
python test_setup.py

# Testes de cen�rios
python test_scenarios.py
```

---

##  Refer�ncias

1. **SPADE Documentation:** https://spade-mas.readthedocs.io/
2. **FIPA Standards:** http://www.fipa.org/repository/standardspecs.html
3. **Q-Learning:** Watkins, C.J.C.H. (1989)
4. **Multi-Agent Systems:** Wooldridge, M. (2009)
5. **Contract Net Protocol:** Smith, R.G. (1980)

---

##  Cr�ditos

**Desenvolvido por:** Rui Almeida  
**Universidade:** [Nome]  
**Disciplina:** Sistemas Multi-Agente  
**Ano:** 2025  
**Framework:** SPADE 3.2.0  
**Python:** 3.12  

---

##  Notas Finais

Este projeto demonstra um sistema completo e funcional de gest�o descentralizada de transportes p�blicos usando:

-  **SPADE** para multi-agente
-  **FIPA CNP** para negocia��o
-  **Machine Learning** para intelig�ncia
-  **Coopera��o V2V** para coordena��o
-  **Dashboard Web** para visualiza��o

O sistema � modular, extens�vel e segue boas pr�ticas de desenvolvimento de software e sistemas multi-agente.

**Total de Features:** 27+  
**Linhas de C�digo:** ~6,325  
**N�vel:** Mestrado / P�s-Gradua��o  
**Status:**  COMPLETO E FUNCIONAL

---

**Fim da Documenta��o** 
