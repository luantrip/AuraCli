# Matriz visual da Aura TUI

Esta pasta contém cenários de eventos válidos e as **frames golden semânticas** derivadas do replay puro. O arquivo `scenarios.json` é a fonte de eventos; `golden_frames.json` fixa activity, conversation, blocking attention, density, drawer mode, runtime phase e visibilidade do loading.

A matriz usa os viewports `(80, 24)`, `(160, 40)`, `(80, 24)` e `(160, 40)` em sequência. Os cenários cobrem stream/resize, sucesso, falha, cancelamento, retomada, aprovação de child task e conclusão em background.

Para verificar o estado versionado:

```bash
.venv/bin/python scripts/generate_visual_goldens.py --check
.venv/bin/python -m pytest -q tests/unit/application/test_visual_golden.py
```

Para atualizar conscientemente o golden após uma mudança de contrato visual:

```bash
.venv/bin/python scripts/generate_visual_goldens.py
```

Os captures SVG de referência do shell idle ficam em `audit_screenshots/phase8/`. Eles são evidência visual humana; o gate automatizado usa as frames semânticas para evitar falsos positivos causados por fontes/renderers diferentes. A captura atual ainda evidencia quadrados em glyphs no renderer; esse risco permanece registrado para tratamento posterior, sem remover conteúdo do golden semântico.
