# 🚌 Sistema Multi-Agente de Transportes Públicos# Multi-Agent Decentralized Public Transportation System



Sistema descentralizado de gestão de transportes públicos usando **SPADE** (Smart Python Agent Development Environment) com Machine Learning e Contract Net Protocol FIPA.## 🚌 Project Overview



## 🎯 FeaturesThis project implements a decentralized public transportation management system using SPADE (Smart Python Agent Development Environment). The system simulates a city's bus and tram network where multiple agents collaborate to optimize schedules, handle disruptions, and ensure efficient service delivery without relying on a central control center.



- ✅ **4 Tipos de Agentes Autónomos** (Estações, Veículos, Passageiros, Manutenção)## 🏗️ Architecture

- ✅ **Machine Learning** (Q-Learning, Demand Prediction, Pattern Recognition)

- ✅ **Contract Net Protocol FIPA** (Negociação descentralizada)### Agent Types

- ✅ **Cooperação Veículo-a-Veículo** (Convoys, Load Balancing)

- ✅ **Dashboard Web em Tempo Real** (Chart.js, Heatmap 20×20)1. **Vehicle Agents (Buses/Trams)**

- ✅ **Otimização Dinâmica de Rotas**   - Operate along routes and manage passenger capacity

- ✅ **Comunicação XMPP** via SPADE   - Adapt schedules based on real-time conditions

   - Negotiate with stations and other vehicles

## 📊 Estatísticas

2. **Station Agents**

- **Linhas de Código:** ~6,325   - Monitor passenger queues and demand

- **Ficheiros Python:** 24   - Request additional vehicles when overcrowded

- **Agentes:** 4 tipos com 20+ behaviours   - Share demand forecasts with nearby stations

- **Algoritmos ML:** 4 (DemandPredictor, QLearning, PatternRecognizer, ReinforcementLearner)

3. **Passenger Agents** (Simulated)

## 🚀 Quick Start   - Generate travel requests with origins and destinations

   - Choose routes dynamically based on availability

### 1. Instalação

4. **Maintenance Crew Agents**

```powershell   - Respond to vehicle breakdowns

# Clone e navega para o diretório   - Prioritize repairs and manage limited resources

cd "c:\Users\Rui Almeida\Desktop\Uni\sistemas"

### Communication Protocols

# Ativa ambiente virtual

.\spade_venv\Scripts\Activate.ps1- **Contract Net Protocol** for task delegation

- **Direct messaging** for status updates

# Instala dependências (se necessário)- **Broadcast messaging** for emergency situations

pip install -r requirements.txt

```## 🚀 Getting Started



### 2. Execução### Prerequisites



**Opção A: Sistema Completo (com XMPP)**- Python 3.8+

```powershell- SPADE framework

python main.py- Virtual environment (recommended)

```

Dashboard disponível em: http://localhost:8080### Installation



**Opção B: Demo Simplificado (sem XMPP)**1. **Activate your virtual environment:**

```powershell   ```powershell

python demo.py   .\spade_venv\Scripts\Activate.ps1

```   ```



## 📁 Estrutura2. **Install dependencies:**

   ```powershell

```   pip install -r requirements.txt

sistemas/   ```

├── main.py                      # Entry point com dashboard

├── demo.py                      # Demo sem XMPP3. **Set up XMPP server (for local testing):**

├── requirements.txt             # Dependências   ```powershell

│   # Install prosody or use localhost XMPP server

├── src/   # For testing, the system will use localhost

│   ├── agents/                  # 4 tipos de agentes SPADE   ```

│   │   ├── station_agent.py     # Estações (373 linhas)

│   │   ├── vehicle_agent.py     # Veículos (418 linhas)### Running the Simulation

│   │   ├── passenger_agent.py   # Passageiros (331 linhas)

│   │   ├── maintenance_agent.py # Manutenção (255 linhas)1. **Start the main simulation:**

│   │   └── cooperation.py       # Cooperação V2V (246 linhas)   ```powershell

│   │   python main.py

│   ├── protocols/   ```

│   │   └── contract_net.py      # CNP FIPA completo (251 linhas)

│   │2. **View the console visualization:**

│   ├── ml/   The system will display a real-time grid showing:

│   │   └── learning.py          # 4 algoritmos ML (389 linhas)   - `B` = Bus

│   │   - `T` = Tram  

│   ├── environment/   - `X` = Broken vehicle

│   │   ├── city.py              # Grid 20×20 (287 linhas)   - `S` = High demand station

│   │   └── route_optimizer.py   # Otimização (245 linhas)   - `s` = Medium demand station

│   │   - `·` = Low demand station

│   └── visualization/

│       └── templates/3. **Stop the simulation:**

│           └── dashboard_advanced.html  # UI (825 linhas)   Press `Ctrl+C` to gracefully stop all agents

│

└── DOCUMENTACAO_COMPLETA.md     # Documentação detalhada (1012 linhas)## 📁 Project Structure

```

```

## 🤖 Agentes Implementadossistemas/

├── main.py                 # Main simulation entry point

### 1. **StationAgent** (Estações)├── requirements.txt        # Python dependencies

- Gere filas de passageiros├── README.md              # This file

- Prevê procura com ML├── hello_agent.py         # SPADE test file

- Inicia Contract Net Protocol quando necessário└── src/

- 5 behaviours assíncronos    ├── agents/            # Agent implementations

    │   ├── base_agent.py      # Base agent class

### 2. **VehicleAgent** (Autocarros/Elétricos)    │   ├── vehicle_agent.py   # Vehicle agents

- Move entre estações    │   ├── station_agent.py   # Station agents

- Transporta passageiros    │   └── maintenance_agent.py # Maintenance crews

- Aprende rotas com Q-Learning    ├── environment/       # City and environment simulation

- Responde a CNP com propostas    │   └── city.py           # City grid and routes

- 7 behaviours assíncronos    ├── protocols/         # Communication protocols

    │   └── contract_net.py   # Contract Net Protocol

### 3. **PassengerAgent** (Passageiros)    ├── simulation/        # Simulation coordination

- Espera na estação    │   └── coordinator.py    # Main simulation coordinator

- Negocia viagem    ├── config/           # Configuration

- Desiste se espera for excessiva    │   └── settings.py      # System configuration

- 4 behaviours assíncronos    ├── metrics/          # Performance tracking

    │   └── collector.py     # Metrics collection

### 4. **MaintenanceAgent** (Manutenção)    └── visualization/    # Visualization tools

- Repara veículos avariados        └── console.py       # Console-based visualization

- Prioriza jobs por urgência```

- 3 behaviours assíncronos

## ⚙️ Configuration

## 🧠 Machine Learning

Edit `src/config/settings.py` to modify:

### DemandPredictor

Previsão multi-sinal com 4 componentes:- **City parameters**: Grid size, number of stations/vehicles

- Padrões por hora (40%)- **Vehicle settings**: Capacity, fuel consumption, breakdown rates

- Tendências recentes (30%)- **Passenger behavior**: Arrival rates, patience times

- Padrões por dia (20%)- **Simulation parameters**: Time steps, duration, rush hours

- Média histórica (10%)

## 📊 Performance Metrics

### QLearningRouter

Rotas inteligentes com epsilon-greedy:The system tracks:

- Estado: (posição, combustível, passageiros)

- Reward: passageiros entregues - tempo espera - combustível- **Average passenger waiting time**

- Exploration decay: 0.995- **Fleet utilization** (percentage of active vehicles)

- **On-time performance** of routes

### PatternRecognizer- **Passenger satisfaction** (successful trips)

- Detecção de rush hour (procura > 1.5× média)- **Collaboration effectiveness**

- Detecção de anomalias (> média + 2σ)- **Breakdown response times**



## 🤝 Contract Net Protocol FIPA## 🧪 Development Phases



Fluxo completo de negociação:### Week 1-2: Foundation ✅

- [x] Basic project structure

```- [x] Agent base classes

1. CFP → Station envia Call for Proposals- [x] City environment simulation

2. PROPOSE → Vehicles enviam propostas competitivas- [x] Basic vehicle and station agents

3. EVALUATE → Station calcula scores (capacity 30%, time 40%, cost 30%)

4. ACCEPT/REJECT → Melhor proposta ganha### Week 3: Communication ✅

5. EXECUTE → Veículo executa contrato- [x] Message passing between agents

6. INFORM → Notifica conclusão- [x] Basic ride allocation logic

```- [x] Enhanced station-vehicle negotiation



## 🚗 Cooperação Veículo-a-Veículo### Week 4: Resource Management ✅

- [x] Vehicle capacity constraints

- **Anúncio de Intenções:** Evita sobreposição- [x] Fuel/energy management

- **Convoy Formation:** Veículos seguem juntos para mesma estação- [x] Dynamic events (traffic, breakdowns)

- **Load Balancing:** Distribui passageiros entre múltiplos veículos- [x] Route adaptation

- **7 Tipos de Mensagens:** INTENTION_ANNOUNCE, CONVOY_INVITE, CONVOY_ACCEPT, LOAD_BALANCE, POSITION_UPDATE, HELP_REQUEST, HELP_RESPONSE

### Week 5: Advanced Protocols ✅

## 📊 Dashboard Web- [x] Contract Net Protocol implementation

- [x] Maintenance crew integration

Interface em tempo real com:- [x] Vehicle rerouting negotiations

- 7 métricas dinâmicas

- 2 gráficos Chart.js (line + doughnut)### Week 6: Visualization & Testing ✅

- Heatmap 20×20 da cidade- [x] Web-based dashboard

- Lista de veículos e estações- [x] Scenario testing (rush hour, breakdowns)

- Eventos de cooperação- [x] Performance evaluation

- Updates a cada 2 segundos- [x] Documentation and reports



**Acesso:** http://localhost:8080## 🎯 Usage Examples



## 🎓 Conceitos Académicos### Basic Simulation

```python

- **Sistemas Multi-Agente:** Autonomia, reatividade, proatividade, habilidade social# Run with default settings

- **FIPA Standards:** Contract Net Protocol, ACLpython main.py

- **Reinforcement Learning:** Q-Learning, epsilon-greedy```

- **Coordenação Descentralizada:** Emergent behavior, peer-to-peer

- **Otimização Distribuída:** Load balancing, resource allocation### Custom Configuration

```python

## 📈 Métricas# Modify settings in src/config/settings.py

SIMULATION_CONFIG['city']['num_vehicles'] = 15

| Métrica | Target | Descrição |SIMULATION_CONFIG['passenger']['arrival_rate'] = 0.5

|---------|--------|-----------|```

| Tempo Espera | < 10 min | Média aceitável |

| Utilização Frota | 60-80% | Ocupação ótima |### Testing Scenarios

| Pontualidade | > 85% | Chegadas a tempo |```python

| Satisfação | > 7/10 | Passageiros satisfeitos |# Rush hour simulation

| Cooperação | > 70% | Sucesso colaboração |# Breakdown events

# High demand events

## 🔧 Configuração```



Editar `src/config/settings.py`:## 🤝 Key Features Implemented



```python- ✅ **Decentralized agent coordination**

SIMULATION_CONFIG = {- ✅ **Real-time passenger queue management**

    'city': {- ✅ **Vehicle breakdown simulation**

        'grid_size': (20, 20),- ✅ **Contract Net Protocol for task delegation**

        'num_stations': 15,- ✅ **Performance metrics collection**

        'num_vehicles': 10,- ✅ **Console visualization**

        'num_passengers': 50,- ✅ **Dynamic route optimization**

        'num_maintenance_crews': 3- ✅ **Web dashboard with real-time updates**

    },- ✅ **Independent Passenger SPADE agents**

    'vehicle': {- ✅ **Automated scenario testing**

        'capacity': 40,

        'breakdown_probability': 0.001## 📝 Notes

    },

    'passenger': {- The system uses localhost XMPP for agent communication

        'patience_time': 15,  # minutos- Passenger agents are simulated within station agents for simplicity

        'arrival_rate': 0.3- Vehicle movement is simplified to grid-based positioning

    }- All agents run asynchronously using SPADE's behavior system

}

```## 🔧 Troubleshooting



## 🧪 Testes**Common Issues:**



```powershell1. **Import errors**: Ensure virtual environment is activated

# Testes de setup2. **XMPP connection**: Verify localhost XMPP server or modify config

python test_setup.py3. **Performance**: Reduce number of agents for testing



# Cenários de teste**Debug Mode:**

python test_scenarios.pySet `log_level: 'DEBUG'` in settings.py for detailed logging.

```

---

## 📚 Documentação Completa

*This project demonstrates multi-agent systems, decentralized coordination, and real-time simulation using SPADE framework.*
Ver **DOCUMENTACAO_COMPLETA.md** para:
- Explicação detalhada de cada agente
- Todos os behaviours implementados
- Algoritmos ML explicados
- Fluxo completo do CNP
- Exemplos de código
- Diagramas de arquitetura

## 🛠️ Tecnologias

- **Python 3.12**
- **SPADE 3.2.0** (Multi-Agent Framework)
- **Aiohttp 3.10.4** (Web Server)
- **Chart.js 4.4.0** (Gráficos)
- **NumPy** (Computação Científica)
- **XMPP** (Comunicação)

## 📝 Requisitos

```
spade==3.2.0
aiohttp==3.10.4
numpy
matplotlib
asyncio-mqtt
```

## ⚠️ Nota sobre XMPP

O sistema requer servidor XMPP (ejabberd ou Prosody). Para testar sem XMPP:
```powershell
python demo.py
```

## 👤 Autor

**Rui Almeida**  
Universidade: [Nome]  
Disciplina: Sistemas Multi-Agente  
Ano: 2025

## 📄 Licença

Este projeto é académico.

## 🎉 Status

✅ **COMPLETO E FUNCIONAL**

- 27+ features implementadas
- ~6,325 linhas de código
- Nível: Mestrado/Pós-Graduação
- 100% dos requisitos cumpridos

---

Para mais detalhes, consultar **DOCUMENTACAO_COMPLETA.md** (1012 linhas de documentação técnica).
