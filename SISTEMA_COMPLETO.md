# 🚌 Sistema Multi-Agente de Transporte Público - ESTADO ATUAL

**Data:** 18 de Novembro de 2025  
**Status:** ✅ **SISTEMA FUNCIONAL E OPERACIONAL**

---

## 📊 RESUMO EXECUTIVO

Sistema multi-agente baseado em SPADE para simulação de transporte público com **28 agentes autónomos** comunicando via ACL (Agent Communication Language) através de message bus local.

### ✅ Componentes Funcionais

1. **Agentes SPADE Autónomos (28 agentes)**
   - 15 Station Agents (estações de autocarros/elétricos)
   - 10 Vehicle Agents (6 autocarros + 4 elétricos)
   - 3 Maintenance Agents (equipas de manutenção)

2. **Local Message Bus**
   - Sistema de comunicação ACL sem necessidade de servidor XMPP
   - Routing automático de mensagens entre agentes
   - Queue assíncrona para cada agente

3. **Behaviors Autónomos (CyclicBehaviours com while True)**
   - MovementBehaviour: veículos movem-se autonomamente
   - MaintenanceMonitoring: verifica saúde dos veículos (breakdown system)
   - BreakdownResponseBehaviour: crews respondem a avarias
   - PassengerManagement: gestão de passageiros
   - DemandForecasting: previsão de procura nas estações

4. **Sistema de Eventos Dinâmicos**
   - Rush hours automáticas
   - Concertos e eventos especiais
   - Traffic jams
   - Weather events
   - Demand surges

5. **Dashboard Web (http://localhost:8080)**
   - Visualização em tempo real
   - Métricas de performance
   - Estado dos agentes

---

## 🏗️ ARQUITETURA

### Fluxo de Comunicação ACL

```
Vehicle (avaria) 
    ↓ BREAKDOWN_ALERT via message_bus
Maintenance Crews (3 recebem)
    ↓ Processam mensagem
    ↓ Criam repair job
    ↓ Priorizam
    ↓ MAINTENANCE_REQUEST (acknowledgment)
Vehicle recebe confirmação
```

### Hierarquia de Classes

```
BaseTransportAgent
├── register_agent() → message_bus
├── send_message() → message_bus.send_message()
└── MessageReceiver → message_bus.receive_message()

VehicleAgent extends BaseTransportAgent
├── MovementBehaviour (loop infinito)
├── MaintenanceMonitoring (loop infinito)
├── PassengerManagement (loop infinito)
├── CapacityNegotiation (loop infinito)
├── RouteAdaptation (loop infinito)
└── ContractNetHandler (loop infinito)

MaintenanceAgent extends BaseTransportAgent
├── BreakdownResponseBehaviour (loop infinito)
├── RepairExecution (loop infinito)
└── JobPrioritization (loop infinito)

StationAgent extends BaseTransportAgent
├── PassengerArrivalSimulation (loop infinito)
├── VehicleMonitoring (loop infinito)
├── DemandForecasting (loop infinito)
├── ServiceRequestManagement (loop infinito)
└── ContractNetHandler (loop infinito)
```

---

## ✅ VALIDAÇÃO DO SISTEMA

### Teste de Comunicação ACL (CONFIRMADO)

**Evidência do Teste:**
```
💥 vehicle_2 has broken down at 5,8 - Type: engine
📡 vehicle_2 sending BREAKDOWN_ALERT to 3 maintenance crews...
📨 Message routed: vehicle2@local → maintenance0@local [Type: breakdown_alert]
✉️ BREAKDOWN_ALERT sent to maintenance0@local
📨 Message routed: vehicle2@local → maintenance1@local [Type: breakdown_alert]
✉️ BREAKDOWN_ALERT sent to maintenance1@local
📨 Message routed: vehicle2@local → maintenance2@local [Type: breakdown_alert]
✉️ BREAKDOWN_ALERT sent to maintenance2@local
📨 maint_0 received BREAKDOWN_ALERT from vehicle2@local
📨 maint_1 received BREAKDOWN_ALERT from vehicle2@local
📨 maint_2 received BREAKDOWN_ALERT from vehicle2@local
🔧 maint_0 received breakdown alert for vehicle_2 (Type: engine, Est. time: 7s)
```

### Funcionalidades Verificadas

- ✅ Agentes inicializam corretamente (28/28)
- ✅ Behaviors executam em loop infinito
- ✅ Veículos movem-se autonomamente entre estações
- ✅ Breakdown system funciona (2% probabilidade)
- ✅ Mensagens ACL enviadas via message bus
- ✅ Maintenance crews recebem e processam mensagens
- ✅ Eventos dinâmicos ativam (rush hours, etc.)
- ✅ Dashboard web acessível

---

## 📁 ESTRUTURA DE FICHEIROS

### Principais Ficheiros

**Core:**
- `main.py` - Entry point, cria agentes e inicia behaviors
- `src/protocols/message_bus.py` - **NOVO** Sistema de mensagens local

**Agentes:**
- `src/agents/base_agent.py` - Classe base com message bus integration
- `src/agents/vehicle_agent.py` - Veículos com 6 behaviors
- `src/agents/maintenance_agent.py` - Crews com 3 behaviors
- `src/agents/station_agent.py` - Estações com 5 behaviors
- `src/agents/passenger_agent.py` - Passageiros (opcional, pode ser desativado)

**Configuração:**
- `src/config/settings.py` - Todas as configurações do sistema

**Ambiente:**
- `src/environment/city.py` - Grid da cidade, rotas, posições
- `src/environment/events.py` - Sistema de eventos dinâmicos
- `src/environment/traffic_manager.py` - Gestão de tráfego

**ML/IA:**
- `src/ml/learning.py` - Q-Learning, demand prediction

**Protocolos:**
- `src/protocols/contract_net.py` - Contract Net Protocol (CNP)
- `src/protocols/message_bus.py` - Local message bus

**Métricas:**
- `src/metrics/collector.py` - Coleta de métricas de performance

---

## 🔧 CONFIGURAÇÕES ATUAIS

```python
SIMULATION_CONFIG = {
    'vehicle': {
        'breakdown_probability': 0.02,  # 2% por verificação
        'fuel_consumption_rate': 0.5,
        'fuel_capacity': 100
    },
    'maintenance': {
        'repair_time_tire': 2,      # segundos
        'repair_time_engine': 7,    # segundos
        'repair_time_tow': 3,       # segundos
        'max_concurrent_repairs': 3
    },
    'passenger': {
        'arrival_rate': 0.3,
        'rush_hour_multiplier': 3.0,
        'patience_time': 15
    }
}
```

---

## 🚀 COMO EXECUTAR

```powershell
# Ativar ambiente virtual
.\spade_venv\Scripts\activate

# Executar sistema
python main.py

# Aceder dashboard
# Abrir navegador em http://localhost:8080
```

**Auto-Stop:** Sistema para automaticamente após 120 segundos em modo de teste.

---

## 📈 PRÓXIMOS PASSOS

### Para a Interface (Dashboard)

1. **Verificar visualização em tempo real**
   - Testar se mostra posições dos veículos
   - Confirmar que breakdowns aparecem no mapa
   - Verificar métricas (passageiros transportados, etc.)

2. **Melhorar UI/UX**
   - Adicionar filtros (mostrar apenas veículos, apenas maintenance)
   - Legend para estados (operacional, avariado, em reparo)
   - Gráficos de performance ao longo do tempo

3. **Logs e Debugging**
   - Painel de logs na interface
   - Timeline de eventos
   - Estado detalhado de cada agente

### Otimizações Futuras

1. **Performance**
   - Reduzir verbose logging em produção
   - Otimizar frequency de checks (alguns behaviors podem ser menos frequentes)

2. **Funcionalidades Adicionais**
   - Passenger agents ativos (desativados por defeito)
   - Dinâmica de combustível mais realista
   - Sistema de custos e budget

3. **Contract Net Protocol**
   - Ativar negociação real entre maintenance crews
   - Crews competem por jobs baseado em distância/disponibilidade

---

## 🐛 PROBLEMAS CONHECIDOS RESOLVIDOS

- ✅ **Behaviors não executavam continuamente** → Adicionado `while True` em todos
- ✅ **Mensagens ACL não funcionavam** → Implementado message bus local
- ✅ **KeyError 'repair_time'** → Corrigido para usar repair_time_TYPE
- ✅ **dispatch_maintenance obsoleto** → Removido (agentes comunicam diretamente)

---

## 📚 DOCUMENTAÇÃO ADICIONAL

- `DOCUMENTACAO_COMPLETA.md` - Documentação detalhada de todos os componentes
- `GUIA_DE_TESTES.md` - Como testar funcionalidades específicas
- `IMPLEMENTACOES_COMPLETAS.md` - Detalhes de implementação
- `XMPP_SETUP.md` - Setup XMPP (não necessário para local mode)

---

## 🎯 CONCLUSÃO

O sistema está **totalmente funcional** com agentes autónomos comunicando via ACL através de message bus local. A arquitetura está bem estruturada, o código está limpo, e o sistema demonstra comportamentos emergentes complexos.

**Estado Final:** ✅ **PRONTO PARA INTERFACE E DEMONSTRAÇÃO**

---

**Desenvolvido com:**
- SPADE Framework (local mode)
- Python 3.11
- aiohttp para dashboard web
- asyncio para concorrência
