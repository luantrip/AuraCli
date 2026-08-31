# 🎨 LLM Paint Agent - Autonomous Art Generation

## 🚀 Novidades

O Paint Agent agora tem **3 modos de geração autônoma** usando LLM!

### 🎯 Modos de Geração

#### 1️⃣ **ASCII Direct** (Rápido, Criativo)
LLM gera arte ASCII completa de uma vez.

**Melhor para:**
- Logos e ícones
- Texto estilizado
- Arte simples
- Geração rápida

**Exemplo:**
```
generate ascii Aura CLI logo
generate ascii cute cat
generate ascii star icon
```

#### 2️⃣ **Primitives** (Preciso, Vetorial)
LLM gera JSON com formas geométricas que são desenhadas com primitivas.

**Melhor para:**
- Diagramas
- UI mockups
- Formas geométricas complexas
- Arte precisa

**Exemplo:**
```
generate primitives geometric pattern
generate primitives house with garden
generate primitives flowchart diagram
```

#### 3️⃣ **Hybrid** (Melhor dos Dois)
Combina ASCII (background/textura) + Primitivas (foreground/shapes).

**Melhor para:**
- Cenas complexas
- Arte com profundidade
- Combinação de estilos
- Máxima qualidade

**Exemplo:**
```
generate hybrid futuristic city
generate hybrid space scene with planets
generate hybrid logo with background
```

#### 🤖 **Auto** (LLM Decide)
LLM escolhe automaticamente o melhor modo.

**Exemplo:**
```
generate llm [qualquer coisa]
```

---

## 📖 Comandos Disponíveis

### Geração LLM

| Comando | Descrição |
|---------|-----------|
| `generate llm [prompt]` | Auto-seleciona melhor modo |
| `generate ascii [prompt]` | Modo ASCII direto |
| `generate primitives [prompt]` | Modo primitivas JSON |
| `generate hybrid [prompt]` | Modo híbrido |
| `refine [feedback]` | Refina última geração |

### Exemplos Práticos

```bash
# Logo
generate llm Aura CLI logo with stars

# Ícone
generate ascii heart icon

# Diagrama
generate primitives system architecture diagram

# Cena complexa
generate hybrid sunset over mountains

# Refinamento iterativo
generate llm robot
refine make it more futuristic
refine add glowing eyes
```

---

## 🔌 Uso em Background (Agentes Chat/AGI)

### Integração Automática

Os agentes **Chat** e **AGI** podem usar a extensão em background:

```python
# Em qualquer agente
from extensions.paint_background_extension import generate_ascii_art

# Gerar arte inline
art = await generate_ascii_art("Aura CLI logo", width=40, height=10)
print(art)

# Gerar ícone pequeno
icon = await generate_icon("star", size=5)

# Gerar logo
logo = await generate_logo("AURA", width=30, height=8)
```

### Ferramentas Disponíveis para Agentes

| Função | Descrição |
|--------|-----------|
| `generate_ascii_art(prompt, width, height, mode)` | Gera arte ASCII |
| `generate_icon(name, size)` | Gera ícone pequeno |
| `generate_logo(text, width, height)` | Gera logo com texto |

### Exemplo de Uso pelo AGI

```python
# AGI Agent pode fazer:
async def create_project_logo(project_name: str):
    """Cria logo para o projeto."""
    logo = await generate_logo(project_name, width=50, height=12)
    
    # Salva em arquivo
    with open(f"{project_name}_logo.txt", "w") as f:
        f.write(logo)
    
    return f"Logo criado: {project_name}_logo.txt"
```

### Cache Inteligente

A extensão usa cache automático:

```python
from extensions.paint_background_extension import get_paint_extension

ext = get_paint_extension()

# Primeira chamada: gera
art1 = await ext.generate("star icon", width=5, height=5)  # Gera

# Segunda chamada: usa cache
art2 = await ext.generate("star icon", width=5, height=5)  # Cached!

# Limpar cache
ext.clear_cache()

# Ver estatísticas
stats = ext.get_cache_stats()
print(stats)  # {"cached_items": 10, "temp_files": 10}
```

---

## 🎨 Fluxo de Trabalho

### 1. Geração Inicial
```
Você: generate llm Aura CLI logo
Agent: ✓ Generated 'Aura CLI logo' using hybrid mode

    ╔═══════════════════════╗
    ║   ▄▀█ █░█ █▀█ ▄▀█    ║
    ║   █▀█ █▄█ █▀▄ █▀█    ║
    ╚═══════════════════════╝
```

### 2. Refinamento Iterativo
```
Você: refine add stars around it
Agent: ✓ Refined with: 'add stars around it'

  ✦ ╔═══════════════════════╗ ✦
    ║   ▄▀█ █░█ █▀█ ▄▀█    ║
  ✦ ║   █▀█ █▄█ █▀▄ █▀█    ║ ✦
    ╚═══════════════════════╝
```

### 3. Ajuste Final
```
Você: refine make colors more vibrant
Agent: ✓ Refined with: 'make colors more vibrant'

[Versão com cores ANSI mais vibrantes]
```

---

## 🔧 Configuração

### Inicializar com LLM Client

```python
from aura_cli.tui.tools.paint.paint import Paint
from aura_cli.tui.tools.paint.paint_agent import PaintAgent
from aura_cli.core.llm.base import get_llm_client

# Criar Paint app
paint_app = Paint()

# Obter LLM client
llm = get_llm_client()

# Criar agent com LLM
agent = PaintAgent(paint_app, llm_client=llm)

# Agora pode usar comandos LLM!
await agent.process_message("generate llm awesome logo")
```

### Usar Extensão em Background

```python
from extensions.paint_background_extension import get_paint_extension
from aura_cli.core.llm.base import get_llm_client

# Obter LLM
llm = get_llm_client()

# Obter extensão
ext = get_paint_extension(llm)

# Gerar arte
result = await ext.generate("robot icon", width=10, height=10)
print(result["art"])
```

---

## 📊 Performance

### Tempos Médios

| Modo | Tempo | Qualidade |
|------|-------|-----------|
| ASCII Direct | ~2-3s | ⭐⭐⭐ |
| Primitives | ~3-5s | ⭐⭐⭐⭐ |
| Hybrid | ~5-8s | ⭐⭐⭐⭐⭐ |

### Cache

- **Hit Rate**: ~80% para prompts repetidos
- **Storage**: Arquivos temporários em `/tmp/aura_paint_bg/`
- **Cleanup**: Automático ao limpar cache

---

## 🎯 Casos de Uso

### 1. Logos de Projetos
```
generate hybrid logo for "MyProject" with tech theme
```

### 2. Ícones para UI
```
generate ascii settings icon
generate ascii user profile icon
generate ascii notification bell
```

### 3. Diagramas
```
generate primitives flowchart with 5 steps
generate primitives network topology
```

### 4. Arte Decorativa
```
generate hybrid space scene with stars and planets
generate ascii border pattern
generate hybrid banner with text "Welcome"
```

### 5. Documentação Visual
```
generate primitives architecture diagram
generate ascii file tree structure
```

---

## 🚀 Próximos Passos

- [ ] Suporte a animações (frames sequenciais)
- [ ] Exportação para SVG
- [ ] Galeria de arte gerada
- [ ] Compartilhamento de prompts
- [ ] Templates pré-definidos
- [ ] Integração com GitHub (logos em README)

---

## 💡 Dicas

1. **Seja específico**: "futuristic robot with glowing eyes" > "robot"
2. **Use refinamento**: Gere primeiro, refine depois
3. **Experimente modos**: Cada modo tem seus pontos fortes
4. **Cache é seu amigo**: Prompts repetidos são instantâneos
5. **Tamanho importa**: Canvas maior = mais detalhes

---

## 🐛 Troubleshooting

### "LLM agent not available"
**Solução**: Inicialize o agent com LLM client:
```python
agent = PaintAgent(paint_app, llm_client=llm)
```

### "Generation failed"
**Possíveis causas**:
- LLM timeout
- JSON parsing error (modo primitives)
- Canvas muito pequeno

**Solução**: Tente outro modo ou aumente canvas.

### Arte cortada
**Solução**: Aumente width/height ou use modo ASCII (auto-ajusta).

---

**Divirta-se criando arte com IA! 🎨✨**
