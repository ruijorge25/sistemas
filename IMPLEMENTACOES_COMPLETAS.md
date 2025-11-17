# 🚌 Sistema de Transporte Multi-Agente - Melhorias Implementadas

## Data: 17 de Novembro de 2025

Este documento descreve todas as funcionalidades implementadas no sistema de transporte multi-agente conforme solicitado.

---

## ✅ 1. Sistema de 3 Bases Off-Grid

### Implementação:
- **Ficheiro Criado**: `src/environment/base_manager.py`
- **Classe Principal**: `BaseManager`

### Funcionalidades:
- **3 Bases Definidas**:
  - **Base de Autocarros**: Entrada/Saída em (0, 10)
  - **Base de Elétricos**: Entrada/Saída em (19, 10)
  - **Base de Manutenção**: Entrada/Saída em (10, 0)

- **Estado dos Agentes**:
  - Novos estados: `'active'` (no mapa) e `'at_base'` (na base, invisível)
  - Veículos em `at_base` não aparecem no dashboard e não contam para congestionamento

- **Spawn/Despawn Logic**:
  - `park_at_base()`: Veículo move-se para ponto de entrada e desaparece do mapa
  - `deploy_from_base()`: Veículo aparece no ponto de entrada quando ativado
  - Controle de capacidade: cada base tem limite de veículos

- **Reabastecimento Automático**:
  - Veículos em `at_base` recebem combustível completo automaticamente
  - Quando combustível < 20, veículo retorna automaticamente à base

### Recursos da Base de Manutenção:
- **3 Veículos de Manutenção** (começam na base)
- **8 Ferramentas** (recurso partilhado)
- **2 Reboques** (recurso partilhado)

---

## ✅ 2. Sistema de Movimento Diferenciado (Carris vs Estradas)

### Implementação:
- **Ficheiro Criado**: `src/environment/traffic_manager.py`
- **Classe Principal**: `TrafficManager`

### Lógica de Elétricos (Carris):
- **Bloqueio por Direção**: Se um elétrico está avariado ou parado, outros elétricos na mesma direção ficam bloqueados
- **Sentidos Opostos Permitidos**: Elétricos em sentidos opostos podem passar pela mesma célula
- **Rails Blocked**: Células com elétricos avariados marcam o carril como bloqueado

### Lógica de Autocarros (Estradas):
- **Ultrapassagem Livre**: Múltiplos autocarros podem ocupar a mesma célula
- **Sem Bloqueio**: Autocarros não bloqueiam uns aos outros
- **Sentidos Opostos**: Também permitidos

### Detecção de Direção:
- Sistema de vetores (dx, dy) para calcular direção do movimento
- Produto escalar para determinar se veículos estão na mesma direção ou direções opostas

---

## ✅ 3. Capacidades Diferenciadas e Overcrowding

### Configurações Atualizadas (`settings.py`):
```python
'bus_capacity': 60,  # Aumentado de 40
'tram_capacity': 40,  # Novo parâmetro
'overcrowding_penalty_bus': 50,  # Limite para penalização
'overcrowding_penalty_tram': 35  # Limite para penalização
```

### Implementação:
- **MockAgent**: Usa capacidade correta baseada em `agent_type`
  - Bus: 60 passageiros
  - Tram: 40 passageiros

### Penalização por Overcrowding:
- Configurado para ser implementado em `passenger_agent.py`
- Quando passageiros > limite, satisfação é penalizada
- Limites: Buses (>50), Trams (>35)

---

## ✅ 4. Sistema de Avarias Detalhadas (3 Tipos)

### Configurações (`settings.py`):
```python
'repair_time_tire': 2,      # 2 segundos
'repair_time_engine': 7,     # 7 segundos
'repair_time_tow': 3,        # 3 segundos
'tools_for_tire': 2,         # 2 ferramentas
'tools_for_engine': 5,       # 5 ferramentas
'tow_hooks_for_tow': 1,      # 1 reboque
```

### Tipos de Avarias:
1. **Pneus (tire)**:
   - Requer: 2 ferramentas
   - Tempo: 2 segundos
   
2. **Motor/Elétrico (engine)**:
   - Requer: 5 ferramentas
   - Tempo: 7 segundos

3. **Reboque (tow)**:
   - Requer: 1 reboque
   - Tempo: 3 segundos

### Lógica de Dispatch:
1. Veículo avaria → tipo aleatório atribuído
2. Sistema verifica recursos disponíveis na base
3. Se recursos suficientes:
   - Veículo de manutenção é deployado da base
   - Recursos são alocados (removidos do pool)
4. Manutenção move-se até o veículo
5. Reparação instantânea ao contato
6. Recursos retornam à base
7. Veículo de manutenção retorna à base

### Gestão de Recursos:
- **Base tem**: 8 ferramentas, 2 reboques
- **Recursos em Uso**: Tracking em tempo real
- **Fila de Avarias**: Se não houver recursos, veículo aguarda

---

## ✅ 5. Visualização de Rotas no Grid

### Implementação:
- **Endpoint Novo**: `/api/routes` retorna todas as rotas
- **Dashboard**: Função `fetchRoutes()` busca rotas ao carregar

### Visualização:
- **Rotas de Bus**: Fundo verde claro com borda pontilhada verde
- **Rotas de Tram**: Fundo azul claro com borda pontilhada azul
- Rotas aparecem como camada de fundo no grid
- Estações e veículos sobrepõem as rotas

### CSS Classes:
```css
.route-bus: rgba(76, 175, 80, 0.3) + border dotted
.route-tram: rgba(33, 150, 243, 0.3) + border dotted
```

---

## ✅ 6. UI Melhorada das Estações

### Tipos de Estações:
- **P (Paragem)**: Apenas autocarros - Verde
- **E (Estação)**: Apenas elétricos - Azul
- **M (Mista)**: Ambos - Roxo

### Lotação Visível:
- Formato: `P 12` (letra + número de passageiros)
- Atualização em tempo real

### Cores Dinâmicas por Demanda:
- **Verde (0-10 passageiros)**: Normal - borda verde
- **Amarelo (11-25 passageiros)**: Cheio - borda amarela
- **Vermelho (>25 passageiros)**: Crítico - borda vermelha + shake animation

### Tamanho Aumentado:
- Células: 40x40px (antes 30x30px)
- Permite mostrar mais informação

---

## ✅ 7. UI Melhorada dos Veículos

### Lotação Dinâmica Visível:
- **Formato**: `B 15/60` ou `T 12/40`
- Primeira linha: Letra do veículo (B ou T)
- Segunda linha: Ocupação atual / Capacidade máxima
- Atualização em tempo real baseada em `len(self.passengers)`

### Informações no Tooltip:
- ID do veículo
- Tipo (Autocarro / Elétrico)
- Lotação (passageiros/capacidade)
- Combustível em %

### Veículos Avariados:
- **Formato**: `X tire` (X + tipo de avaria)
- Cores vermelhas
- Animação de shake
- Tooltip mostra tipo de avaria

---

## ✅ 8. Controlos Manuais no Dashboard

### 3 Botões Implementados:

#### 1. 🚨 Iniciar Hora de Ponta
- **Endpoint**: `POST /api/trigger/rush_hour`
- **Ação**: Adiciona 10-20 passageiros em cada estação
- **Flag**: `rush_hour_active = True`
- **Efeito**: Taxa de chegada de passageiros ×3

#### 2. 💥 Criar Avaria Aleatória
- **Endpoint**: `POST /api/trigger/breakdown`
- **Ação**: Escolhe veículo ativo aleatório e causa avaria
- **Tipo**: Aleatório (tire/engine/tow)
- **Resposta**: Informa qual veículo avariou

#### 3. 🌧️ Ativar/Desativar Chuva
- **Endpoint**: `POST /api/trigger/weather`
- **Ação**: Toggle do estado de chuva
- **Botão**: Muda texto (Ativar ↔ Desativar)

### Feedback Visual:
- Área de status abaixo dos botões
- Mensagens de sucesso (verde) ou erro (vermelho)
- Auto-desaparece após 5 segundos

---

## ✅ 9. Efeitos de Clima (Chuva)

### Implementação:
- **Flag**: `weather_active` em `DemoSimulation` e `City`
- **Métodos**: `activate_weather()` e `deactivate_weather()`

### Efeitos da Chuva:
1. **Redução de Velocidade**: 50%
   - `speed_modifier = 0.5` quando chuva ativa
   - Veículos movem-se apenas 50% das vezes

2. **Aumento de Avarias**: +20%
   - `breakdown_modifier = 1.2`
   - Probabilidade base (0.15%) × 1.2 = 0.18%

### Integração:
- Calculado em `update_simulation()`
- Aplicado a todos os veículos ativos
- Visível nos logs do console

---

## ✅ 10. Sistema de Consumo de Combustível

### Configuração:
```python
'fuel_capacity': 100,
'fuel_consumption_per_cell': 1  # 1 unidade por célula
```

### Implementação:
1. **Consumo**: 1 unidade de combustível cada vez que veículo se move
2. **Alertaautomático**: Quando fuel < 20, veículo retorna à base
3. **Movimento para Base**: Veículo calcula caminho para ponto de entrada da sua base
4. **Reabastecimento**: Ao chegar à base, combustível volta a 100
5. **Estado at_base**: Veículo desaparece do mapa durante reabastecimento

### Lógica:
```python
if vehicle.fuel_level < 20:
    # Move towards base
    base_entry = self.base_manager.get_entry_point(base_type)
    # ... movimento ...
    if at_entry_point:
        self.base_manager.park_at_base(vehicle.id, base_type)
        vehicle.state = 'at_base'
        vehicle.fuel_level = 100  # Reabastecimento
```

---

## 📁 Ficheiros Criados/Modificados

### Novos Ficheiros:
1. `src/environment/base_manager.py` - Gestão das 3 bases
2. `src/environment/traffic_manager.py` - Lógica de movimento diferenciado

### Ficheiros Modificados:
1. `src/config/settings.py`
   - Novas capacidades (bus:60, tram:40)
   - Configurações de avarias detalhadas
   - Configurações de clima
   - Novos message types

2. `src/environment/city.py`
   - Suporte para station_types
   - Métodos de clima
   - Hash para Position

3. `demo.py`
   - Integração com BaseManager
   - Integração com TrafficManager
   - Lógica completa de avarias e recursos
   - Sistema de combustível
   - Endpoints de controle manual
   - Estado 'at_base' para agentes

4. `src/visualization/templates/dashboard_advanced.html`
   - Células maiores (40x40px)
   - Visualização de rotas
   - Tipos de estações (P/E/M)
   - Lotação em veículos e estações
   - Cores dinâmicas por demanda
   - Botões de controle manual
   - Funções JavaScript para controles
   - Legenda atualizada

---

## 🎮 Como Usar

### Iniciar o Sistema:
```bash
cd "c:\Users\Rui Almeida\Desktop\Uni\sistemas"
.\spade_venv\Scripts\Activate.ps1
python demo.py
```

### Acessar Dashboard:
```
http://localhost:9000
```

### Usar Controles Manuais:
1. **Hora de Ponta**: Clique no botão para adicionar muitos passageiros
2. **Avaria**: Clique para causar avaria aleatória num veículo
3. **Chuva**: Clique para ativar/desativar efeitos climáticos

### Observar:
- **Grid 20x20**: Mostra veículos, estações, rotas e manutenção
- **Veículos**: Mostram B/T com lotação (ex: "B 15/60")
- **Estações**: Mostram P/E/M com passageiros (ex: "M 12")
- **Manutenção**: Mostra M quando ativa no mapa
- **Avarias**: Mostra X com tipo (ex: "X tire")
- **Console**: Mostra logs de avarias, reparações, bases, combustível

---

## 🔍 Detalhes Técnicos

### Sistema de Bases:
- 3 bases permanentemente off-grid
- Veículos spawnam/despawnam nos pontos de entrada
- Tracking de quais agentes estão em cada base
- Reabastecimento automático quando at_base

### Sistema de Recursos:
- Pool compartilhado de ferramentas (8 total)
- Pool compartilhado de reboques (2 total)
- Sistema de alocação/liberação
- Fila automática quando recursos insuficientes

### Sistema de Movimento:
- TrafficManager rastreia todas as posições
- Bloqueio inteligente para trams (carris)
- Ultrapassagem livre para buses (estradas)
- Detecção de direção por vetores

### Sistema de Avarias:
- 3 tipos com requisitos diferentes
- Dispatch automático de manutenção
- Gestão de recursos
- Reparação instantânea ao contato
- Retorno automático à base

### Dashboard:
- Atualização a cada 2 segundos
- 7 endpoints API (/vehicles, /stations, /metrics, /status, /routes, /bases, /trigger/*)
- Visualização em tempo real
- Controlos interativos

---

## 📊 Métricas Observáveis

### No Console:
- 🏠 Veículos estacionados/deployados
- 💥 Avarias com tipo e posição
- 🚑 Dispatch de manutenção com recursos
- ✅ Reparações completadas
- ⛽ Retornos à base para reabastecimento
- 🔧 Alocação/liberação de recursos
- 🌧️ Ativação/desativação de clima
- 🚨 Eventos de hora de ponta

### No Dashboard:
- Lotação de veículos em tempo real
- Passageiros em estações
- Veículos ativos vs. avariados vs. na base
- Combustível dos veículos
- Rotas visualizadas
- Status de recursos da base de manutenção

---

## ✅ Status Final

**TODAS AS 11 FUNCIONALIDADES FORAM IMPLEMENTADAS COM SUCESSO**

1. ✅ Sistema de 3 bases off-grid
2. ✅ Movimento diferenciado (carris vs estradas)
3. ✅ Capacidades (Bus:60, Tram:40)
4. ✅ Avarias detalhadas (3 tipos)
5. ✅ Visualização de rotas
6. ✅ UI melhorada de estações
7. ✅ UI melhorada de veículos
8. ✅ Controlos manuais
9. ✅ Efeitos de clima
10. ✅ Consumo de combustível
11. ✅ Sistema testado e funcional

**Sistema pronto para uso!** 🎉
