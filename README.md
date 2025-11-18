# Multi-Agent Transportation System

Sistema multi-agente para simulação de transporte público com SPADE, implementando:
- 🚌 **Veículos autónomos** (buses e trams) que se movem ao longo de rotas
- 🚉 **Estações inteligentes** que gerem filas de passageiros e reportam procura
- 👤 **Agentes passageiros** que avaliam e selecionam rotas
- 🔧 **Equipas de manutenção** que respondem a avarias via Contract Net Protocol
- 📊 **Dashboard web** para visualização em tempo real

## Arquitetura

### Agentes SPADE
- **VehicleAgent**: Movimento, gestão de passageiros, monitorização de saúde
- **StationAgent**: Filas de espera, previsão de procura, comunicação com veículos
- **PassengerAgent**: Seleção de rotas, pedidos de embarque
- **MaintenanceAgent**: Contract Net Protocol, priorização de tarefas

### Componentes
- **Message Subscription System**: Sistema de routing de mensagens com queues dedicadas por behavior
- **RouteOptimizer**: Otimização de rotas com machine learning
- **EventManager**: Eventos dinâmicos (congestionamento, rush hour, acidentes)
- **MetricsCollector**: Recolha e agregação de métricas de performance

### Modo de Operação
✅ **XMPP MODE**: O sistema comunica via XMPP/Jabber real usando SPADE.
- Agents conectam-se a servidor XMPP via `agent.start()`
- Comunicação via ACL messages (FIPA-compliant)
- Subscription system garante entrega sem race conditions
- Requer Prosody ou Ejabberd a correr em `localhost:5222`

## Instalação

### Requisitos
- Python 3.12+
- Virtual environment (recomendado)
- **XMPP Server** (Prosody ou Ejabberd)

### Setup Python Environment
```powershell
# Criar virtual environment
python -m venv spade_venv

# Ativar
.\spade_venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

### Setup XMPP Server (Prosody)

#### Windows (via Chocolatey)
```powershell
choco install prosody
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install prosody
```

#### Configuração Prosody
Editar `/etc/prosody/prosody.cfg.lua` (Linux) ou `C:\Program Files\Prosody\prosody.cfg.lua` (Windows):

```lua
VirtualHost "localhost"
    authentication = "internal_plain"
    
c2s_require_encryption = false
s2s_require_encryption = false
```

Criar contas para os 48 agentes:
```bash
# Stations (15)
sudo prosodyctl register station0 localhost spade123
sudo prosodyctl register station1 localhost spade123
# ... (station2-station14)

# Vehicles (10)
sudo prosodyctl register vehicle0 localhost spade123
# ... (vehicle1-vehicle9)

# Passengers (20)
sudo prosodyctl register passenger0 localhost spade123
# ... (passenger1-passenger19)

# Maintenance (3)
sudo prosodyctl register maintenance0 localhost spade123
sudo prosodyctl register maintenance1 localhost spade123
sudo prosodyctl register maintenance2 localhost spade123
```

Script automático (Linux/Mac):
```bash
#!/bin/bash
for i in {0..14}; do sudo prosodyctl register station$i localhost spade123; done
for i in {0..9}; do sudo prosodyctl register vehicle$i localhost spade123; done
for i in {0..19}; do sudo prosodyctl register passenger$i localhost spade123; done
for i in {0..2}; do sudo prosodyctl register maintenance$i localhost spade123; done
```

Iniciar Prosody:
```bash
# Linux
sudo systemctl start prosody
sudo systemctl status prosody

# Windows
net start Prosody
```

## Execução

```powershell
# 1. Verificar Prosody está a correr
# Windows: net start Prosody
# Linux: sudo systemctl status prosody

# 2. Ativar ambiente Python
.\spade_venv\Scripts\activate

# 3. Executar sistema
python main.py
```

O sistema inicia:
- 48 agentes SPADE conectam-se a `localhost:5222` via XMPP
- Dashboard web em http://localhost:8080
- Behaviors iniciam automaticamente via `agent.start()`

### Outputs Esperados
```
🔑 Using XMPP server: localhost:5222
🌐 Domain: localhost
🎬 Starting agents with XMPP connection...
✅ Started 48 agents with XMPP!
🚌 vehicle_X arrived at station (x,y)
👤 Passenger pass_X selected route: bus_route_Y
💥 vehicle_X has broken down - Type: tire
🔧 Repairing vehicle_X - 45s remaining
⏱️ Uptime: 1m - 48 agents active
```

## Testes

```powershell
# Executar testes unit\u00e1rios
pytest tests/ -v

# Apenas testes de subscri\u00e7\u00e3o
pytest tests/test_message_subscription.py -v
```

Testes cobrem:
- ✅ Mensagens chegam a subscribers corretos
- ✅ Múltiplos subscribers recebem cópias independentes
- ✅ Filtering por message type funciona
- ✅ Log queue recebe todas as mensagens
- ✅ Race conditions prevenidas (50 mensagens concorrentes)

## Dashboard

Aceder a **http://localhost:8080** para visualizar:
- Posições de veículos em tempo real
- Estado das estações (passageiros em espera)
- Métricas de performance (on-time arrival rate, average wait time)
- Estado das maintenance bases

### API Endpoints
- `GET /api/status` - Estado geral do sistema
- `GET /api/vehicles` - Dados de todos os veículos
- `GET /api/stations` - Estado das estações
- `GET /api/metrics` - Métricas agregadas
- `GET /api/bases` - Maintenance bases e veículos estacionados

## Estrutura do Projeto

```
sistemas/
├── main.py                    # Entry point principal
├── requirements.txt           # Dependências Python
├── src/
│   ├── agents/               # Implementação dos agentes SPADE
│   │   ├── vehicle_agent.py
│   │   ├── station_agent.py
│   │   ├── passenger_agent.py
│   │   └── maintenance_agent.py
│   ├── config/
│   │   └── settings.py       # Configuração do sistema
│   ├── environment/          # Gestão da cidade e eventos
│   │   ├── city.py
│   │   ├── events.py
│   │   ├── traffic_manager.py
│   │   └── route_optimizer.py
│   ├── metrics/
│   │   └── collector.py      # Recolha de métricas
│   ├── ml/
│   │   └── learning.py       # Machine learning (Q-learning)
│   ├── protocols/
│   │   ├── message_bus.py    # LocalMessageBus (substitui XMPP)
│   │   └── contract_net.py   # Contract Net Protocol
│   └── visualization/
│       └── templates/
│           └── dashboard_advanced.html
└── spade_venv/               # Virtual environment (não versionado)
```

## Configuração

### `src/config/settings.py`

Principais parâmetros ajustáveis:
```python
SIMULATION_CONFIG = {
    'simulation': {
        'time_step': 1.0,        # Segundos por step
        'grid_size': (20, 20)    # Tamanho da grelha
    },
    'vehicle': {
        'speed': 1.0,            # Células por step
        'bus_capacity': 60,
        'tram_capacity': 100,
        'fuel_consumption_rate': 1.0
    },
    'passenger': {
        'arrival_rate': 0.8      # Probabilidade de gerar passageiro
    }
}
```

## Desenvolvimento

### Adicionar Novo Tipo de Veículo
1. Extender `VehicleAgent` em `src/agents/vehicle_agent.py`
2. Definir capacidade e características em `settings.py`
3. Atualizar criação de veículos em `main.py`

### Adicionar Novo Evento
1. Criar classe em `src/environment/events.py`
2. Registar no `EventScheduler` em `main.py`
3. Agentes respondem via `event_manager.get_traffic_modifier()`

## Limitações Conhecidas

1. **Sem XMPP Real**: Agentes não podem ser distribuídos por múltiplos processos/máquinas
2. **LocalMessageBus**: Substituição local que não escala para sistemas distribuídos
3. **Behaviors Manuais**: `asyncio.create_task(behavior.run())` em vez de framework SPADE nativo
4. **Passageiros não embarcam**: Sistema de boarding via ACL messages está incompleto
5. **Crash após start**: Sistema pode terminar inesperadamente (KeyboardInterrupt)

## Troubleshooting

### Veículos não se movem
✅ **RESOLVIDO**: Behaviors agora são iniciados corretamente com `asyncio.create_task(behavior.run())`

### Dashboard mostra 0 passageiros
- Passageiros avaliam rotas mas não enviam boarding requests completos
- StationAgent.passenger_queue pode estar vazia (sem arrival_rate alta)

### Sistema crasha após iniciar
- Exception em algum behavior não está a ser capturada
- Verificar logs completos com `python main.py 2>&1 | Select-Object -First 200`

### Port 8080 já em uso
```powershell
Get-Process python | Stop-Process -Force
```

## Métricas e Performance

O `MetricsCollector` calcula:
- **Average Wait Time**: Tempo médio de passageiros em filas
- **On-Time Arrival Rate**: % de veículos que chegam no tempo estimado
- **System Efficiency**: Métrica agregada de performance
- **Breakdown Rate**: Frequência de avarias

Acessível via `/api/metrics` ou no dashboard.

## Licença

Projeto académico - Universidade [Nome] - Sistemas Multi-Agente 2025
