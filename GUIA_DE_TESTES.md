# 🧪 Guia de Teste - Sistema de Transporte

## Checklist de Validação

### ✅ Teste 1: Servidor e Dashboard
- [ ] Servidor inicia sem erros
- [ ] Dashboard carrega em http://localhost:9000
- [ ] Grid 20x20 aparece
- [ ] Métricas atualizam a cada 2 segundos
- [ ] Gráficos funcionam

### ✅ Teste 2: Visualização de Veículos
- [ ] Autocarros aparecem como "B" (verde)
- [ ] Elétricos aparecem como "T" (azul)
- [ ] Lotação visível: "B 15/60" ou "T 12/40"
- [ ] Veículos movem-se no grid
- [ ] Tooltip mostra informações completas

### ✅ Teste 3: Visualização de Estações
- [ ] Estações mostram tipo: P (bus), E (tram), ou M (mista)
- [ ] Número de passageiros visível: "M 12"
- [ ] Cores mudam com demanda:
  - Verde: 0-10 passageiros
  - Amarelo: 11-25 passageiros
  - Vermelho: >25 passageiros
- [ ] Estações em vermelho têm animação de shake

### ✅ Teste 4: Sistema de Bases
**Verificar no Console:**
- [ ] Mensagem inicial: "🏠 maint_0 parked at Maintenance Base" (3×)
- [ ] Mensagem: "✅ Setup complete: 10 vehicles, 15 stations, 3 maintenance crews at base"

**Observar no Dashboard:**
- [ ] Nenhum veículo de manutenção visível no início (estão na base)
- [ ] Endpoint /api/bases retorna status das bases

### ✅ Teste 5: Sistema de Avarias
**Aguardar ou usar botão "Criar Avaria Aleatória":**
- [ ] Console mostra: "💥 vehicle_X broke down at (x, y) - Type: tire/engine/tow"
- [ ] Veículo muda para "X" vermelho no grid
- [ ] Tipo de avaria visível: "X tire", "X engine", ou "X tow"

### ✅ Teste 6: Sistema de Manutenção
**Após avaria:**
- [ ] Console mostra: "🚑 maint_X deployed from base to repair vehicle_Y (breakdown_type)"
- [ ] Console mostra recursos: "Resources: X tools, Y tow hooks"
- [ ] Veículo de manutenção aparece como "M" (laranja) no grid
- [ ] "M" move-se em direção ao veículo avariado
- [ ] Ao chegar: "✅ maint_X successfully repaired vehicle_Y"
- [ ] Console mostra: "✅ Resources released: X tools, Y tow hooks"
- [ ] "M" retorna à base: "🏠 maint_X returned to base"

### ✅ Teste 7: Gestão de Recursos
**Causar múltiplas avarias rapidamente:**
- [ ] Se avaria tipo "engine" (5 ferramentas):
  - Base tem 8 ferramentas
  - Depois de 1 repair: restam 3 ferramentas
  - Próxima avaria "engine" NÃO pode ser atendida
  - Console mostra: "⚠️ Insufficient resources!"
- [ ] Após reparação, recursos voltam e próxima avaria pode ser atendida

### ✅ Teste 8: Sistema de Combustível
**Observar veículos durante ~5-10 minutos:**
- [ ] Veículos consomem combustível ao mover-se
- [ ] Quando fuel < 20, veículo move-se para sua base
- [ ] Console mostra: "⛽ vehicle_X returned to base for refueling"
- [ ] Veículo desaparece do grid (estado at_base)
- [ ] Após reabastecimento, pode reaparecer

### ✅ Teste 9: Movimento Diferenciado
**Trams (Elétricos):**
- [ ] Se elétrico avaria, bloqueia o carril
- [ ] Console mostra: "🚫 Rail blocked at (x, y) due to broken tram"
- [ ] Outros elétricos na mesma direção não podem passar
- [ ] Elétricos em direção oposta PODEM passar
- [ ] Após reparação: "✅ Rail unblocked at (x, y)"

**Buses (Autocarros):**
- [ ] Múltiplos autocarros podem ocupar mesma célula
- [ ] Autocarros não bloqueiam uns aos outros
- [ ] Podem ultrapassar livremente

### ✅ Teste 10: Botão "Iniciar Hora de Ponta"
- [ ] Clicar no botão "🚨 Iniciar Hora de Ponta"
- [ ] Todas as estações ganham 10-20 passageiros
- [ ] Números nas estações aumentam
- [ ] Muitas estações ficam amarelas/vermelhas
- [ ] Console mostra: "🚨 RUSH HOUR TRIGGERED"
- [ ] Mensagem de sucesso aparece abaixo dos botões

### ✅ Teste 11: Botão "Criar Avaria Aleatória"
- [ ] Clicar no botão "💥 Criar Avaria Aleatória"
- [ ] Um veículo ativo aleatório avaria
- [ ] Console mostra: "💥 MANUAL BREAKDOWN: vehicle_X - Type: tire/engine/tow"
- [ ] Veículo vira "X" vermelho no grid
- [ ] Sistema de manutenção é ativado automaticamente
- [ ] Mensagem mostra qual veículo avariou

### ✅ Teste 12: Botão "Ativar Chuva"
**Primeira vez (Ativar):**
- [ ] Clicar no botão "🌧️ Ativar Chuva"
- [ ] Console mostra: "🌧️ Weather activated: rain"
- [ ] Botão muda texto para "☀️ Desativar Chuva"
- [ ] Mensagem: "Rain activated - 50% speed reduction, 20% more breakdowns"
- [ ] Veículos movem-se mais devagar (visível no grid)
- [ ] Mais avarias ocorrem (observar console)

**Segunda vez (Desativar):**
- [ ] Clicar no botão "☀️ Desativar Chuva"
- [ ] Console mostra: "☀️ Weather cleared"
- [ ] Botão volta para "🌧️ Ativar Chuva"
- [ ] Veículos voltam à velocidade normal
- [ ] Avarias reduzem para taxa normal

### ✅ Teste 13: Visualização de Rotas
- [ ] Rotas de bus aparecem com fundo verde claro
- [ ] Rotas de tram aparecem com fundo azul claro
- [ ] Rotas têm bordas pontilhadas
- [ ] Rotas aparecem atrás de estações e veículos

### ✅ Teste 14: Capacidades Diferenciadas
**Autocarros:**
- [ ] Capacidade máxima: 60 passageiros
- [ ] Display: "B X/60"
- [ ] Tooltip confirma: "X/60 passageiros"

**Elétricos:**
- [ ] Capacidade máxima: 40 passageiros
- [ ] Display: "T X/40"
- [ ] Tooltip confirma: "X/40 passageiros"

### ✅ Teste 15: Integração Completa
**Cenário Completo:**
1. [ ] Iniciar servidor
2. [ ] Abrir dashboard
3. [ ] Ativar chuva (botão)
4. [ ] Iniciar hora de ponta (botão)
5. [ ] Criar 2-3 avarias manuais (botão)
6. [ ] Observar:
   - Estações ficam vermelhas (muitos passageiros)
   - Múltiplas avarias ocorrem
   - Múltiplos veículos de manutenção aparecem
   - Recursos são geridos corretamente
   - Veículos são reparados
   - Manutenção volta à base
   - Veículos com baixo combustível voltam à base
   - Sistema continua funcionando

---

## 🐛 Problemas Conhecidos

### Issue 1: Invoke-WebRequest mata o servidor
- **Causa**: PowerShell Invoke-WebRequest causa KeyboardInterrupt
- **Solução**: Testar APIs através do browser ou Postman
- **Workaround**: Usar curl ou navegador para testar endpoints

---

## 📝 Notas de Teste

### Console Logs Importantes:
```
🏠 maint_X parked at Maintenance Base
💥 vehicle_X broke down at (x, y) - Type: tire
🚑 maint_X deployed from base to repair vehicle_Y (tire)
   Resources: 2 tools, 0 tow hooks
✅ maint_X successfully repaired vehicle_Y
✅ Resources released: 2 tools, 0 tow hooks
🏠 maint_X returned to base
⛽ vehicle_X returned to base for refueling
🚫 Rail blocked at (x, y) due to broken tram
✅ Rail unblocked at (x, y)
🌧️ Weather activated: rain
☀️ Weather cleared
🚨 RUSH HOUR TRIGGERED - Extra passengers added to all stations!
💥 MANUAL BREAKDOWN: vehicle_X - Type: engine
⚠️ Insufficient resources! Need X tools and Y tow hooks
⚠️ No maintenance vehicles available at base for vehicle_X
```

### API Endpoints para Testar:
```
GET  http://localhost:9000/              → Dashboard
GET  http://localhost:9000/api/vehicles  → Lista veículos
GET  http://localhost:9000/api/stations  → Lista estações
GET  http://localhost:9000/api/metrics   → Métricas do sistema
GET  http://localhost:9000/api/status    → Status geral
GET  http://localhost:9000/api/routes    → Rotas (novo)
GET  http://localhost:9000/api/bases     → Status das bases (novo)
POST http://localhost:9000/api/trigger/rush_hour   → Hora de ponta
POST http://localhost:9000/api/trigger/breakdown   → Avaria manual
POST http://localhost:9000/api/trigger/weather     → Toggle chuva
```

---

## ✅ Critérios de Sucesso

Sistema está funcional se:
1. ✅ Servidor inicia sem erros
2. ✅ Dashboard carrega e atualiza
3. ✅ Veículos movem-se e mostram lotação
4. ✅ Estações mostram tipo e passageiros
5. ✅ Avarias ocorrem e são exibidas
6. ✅ Manutenção é dispatched automaticamente
7. ✅ Recursos são geridos corretamente
8. ✅ Veículos retornam à base para combustível
9. ✅ Trams bloqueiam carris, buses ultrapassam
10. ✅ Botões de controle funcionam
11. ✅ Chuva afeta velocidade e avarias
12. ✅ Console mostra logs informativos

**Se todos os itens acima estiverem OK, o sistema está 100% funcional! 🎉**
