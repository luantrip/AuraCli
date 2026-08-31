# AuraPaint Helpers

Funções auxiliares do AuraPaint, organizadas por categoria.

## Módulos

- `drawing_helpers.py` — operações de desenho: ponto, linha, retângulo, elipse, fill, seleção
- `error_handlers.py` — tratamento de erros e exibição de mensagens ao usuário
- `undo_helpers.py` — criação de estados de undo/redo e snapshot de canvas

## Uso

Os helpers são implementados como métodos da classe `AuraPaint` em `paint.py`. Os arquivos aqui definem as funções auxiliares que suportam essa implementação e podem ser usados diretamente para teste unitário das operações de desenho sem instanciar a aplicação TUI completa.

```python
from aura_cli.tui.tools.paint.helpers.drawing_helpers import _draw_point_tool

affected_region = _draw_point_tool(
    stamp_brush=brush,
    mouse_at=start,
    mouse_pos=Offset(event.x, event.y),
    affected_region=region,
)
```
