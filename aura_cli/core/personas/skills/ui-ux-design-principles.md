---
name: Foundational Principles of UI/UX Design
description: Use this skill as a guide for designing and evaluating user interfaces. It covers fundamental principles of UI/UX design, including Nielsen's Heuristics, visual hierarchy, feedback, and consistency, ensuring the creation of intuitive, efficient, and user-friendly interfaces.
version: 1.0.0
author: Aura Core Team
---

# Guia de Referência: Princípios Fundamentais de Design de UI/UX

Este guia consolida os princípios essenciais para a criação de interfaces de usuário (UI) e experiências de usuário (UX) de alta qualidade. Ele serve como uma base para tomar decisões de design informadas.

## 1. As 10 Heurísticas de Usabilidade de Nielsen

Estas são as 10 regras gerais mais importantes para o design de interfaces, propostas por Jakob Nielsen.

### 1. Visibilidade do Status do Sistema
**O sistema deve sempre manter os usuários informados sobre o que está acontecendo, através de feedback apropriado e em tempo razoável.**
*   **Exemplos:** Indicadores de carregamento (spinners), barras de progresso, mensagens "toast" (`app.notify`), estado de seleção visível (highlight).

### 2. Correspondência entre o Sistema e o Mundo Real
**O sistema deve falar a linguagem do usuário, com palavras, frases e conceitos familiares, em vez de termos orientados ao sistema.**
*   **Exemplos:** Usar um ícone de lixeira para exclusão, usar termos como "Salvar" e "Cancelar" em vez de "Commit" e "Abort". A interface deve seguir as convenções do mundo real.

### 3. Controle e Liberdade do Usuário
**Os usuários frequentemente escolhem funções do sistema por engano e precisarão de uma "saída de emergência" claramente marcada para sair do estado indesejado sem ter que passar por um diálogo extenso.**
*   **Exemplos:** Funcionalidades de "Desfazer" (Undo) e "Refazer" (Redo), um botão "Cancelar" claro em diálogos modais, um "X" para fechar janelas.

### 4. Consistência e Padrões
**Os usuários não deveriam ter que se perguntar se palavras, situações ou ações diferentes significam a mesma coisa.**
*   **Exemplos:** Um botão "Salvar" deve ter a mesma aparência e localização em todas as telas. A terminologia e os ícones devem ser consistentes em toda a aplicação. Siga as convenções da plataforma (ex: atalhos de teclado padrão).

### 5. Prevenção de Erros
**Melhor do que boas mensagens de erro é um design cuidadoso que previne a ocorrência do problema em primeiro lugar.**
*   **Exemplos:** Desabilitar um botão "Salvar" até que todos os campos obrigatórios estejam preenchidos. Usar um seletor de data em vez de um campo de texto livre. Pedir confirmação antes de ações destrutivas ("Você tem certeza de que deseja excluir?").

### 6. Reconhecimento em Vez de Memorização
**Minimize a carga de memória do usuário, tornando objetos, ações e opções visíveis. O usuário não deve ter que se lembrar de informações de uma parte do diálogo para outra.**
*   **Exemplos:** Menus claramente visíveis, exibir o caminho de navegação ("breadcrumbs"), mostrar itens recentemente visualizados. A ajuda contextual é melhor do que um manual extenso.

### 7. Flexibilidade e Eficiência de Uso
**A interface deve ser eficiente tanto para usuários novatos quanto para experientes. Permita que os usuários personalizem ações frequentes.**
*   **Exemplos:** Fornecer atalhos de teclado (aceleradores) para usuários avançados, enquanto a navegação via menus permanece clara para novatos. Implementar uma "Paleta de Comandos".

### 8. Design Estético e Minimalista
**Os diálogos não devem conter informações irrelevantes ou raramente necessárias. Cada unidade extra de informação em um diálogo compete com as unidades relevantes e diminui sua visibilidade relativa.**
*   **Exemplos:** Manter a UI limpa e focada na tarefa principal. Usar espaços em branco de forma eficaz para agrupar elementos relacionados e guiar o olho do usuário. Priorizar o conteúdo.

### 9. Ajudar os Usuários a Reconhecer, Diagnosticar e se Recuperar de Erros
**As mensagens de erro devem ser expressas em linguagem clara (sem códigos de erro), indicar precisamente o problema e sugerir construtivamente uma solução.**
*   **Exemplo Ruim:** "Erro -271".
*   **Exemplo Bom:** "Senha Inválida. Sua senha precisa ter pelo menos 8 caracteres, incluindo uma letra maiúscula e um número."

### 10. Ajuda e Documentação
**Mesmo que seja melhor que o sistema possa ser usado sem documentação, pode ser necessário fornecer ajuda e documentação.**
*   **Exemplos:** Tooltips (dicas de ferramenta) em ícones, um tour de "primeiros passos" (onboarding), uma seção de "Ajuda" ou "FAQ" facilmente acessível.

## 2. Outros Princípios Essenciais de Design de UI

### Hierarquia Visual
A hierarquia visual é um dos princípios mais importantes por trás de um bom design. É a ordem em que o olho humano percebe o que vê.
*   **Tamanho:** Elementos maiores atraem mais atenção.
*   **Cor:** Cores brilhantes e contrastantes se destacam mais do que cores suaves e sem contraste.
*   **Alinhamento:** Elementos alinhados criam uma sensação de ordem e conexão.
*   **Repetição:** Repetir estilos para elementos relacionados cria consistência.
*   **Proximidade:** Agrupar elementos relacionados os faz parecer uma única unidade.
*   **Espaço em Branco (Espaço Negativo):** O espaço vazio ao redor dos elementos é tão importante quanto os próprios elementos. Ele reduz o ruído visual e melhora a legibilidade.

### Lei de Fitts
**O tempo para adquirir um alvo é uma função da distância e do tamanho do alvo.**
*   **Aplicação:** Botões e outros alvos clicáveis devem ser grandes o suficiente para serem facilmente selecionados. Elementos relacionados devem estar próximos uns dos outros. Os cantos e bordas da tela são os locais mais fáceis e rápidos de alcançar.

### Lei de Hick
**O tempo que leva para tomar uma decisão aumenta com o número e a complexidade das escolhas.**
*   **Aplicação:** Minimize o número de opções quando a resposta do usuário precisa ser rápida. Quebre tarefas complexas em etapas menores com menos opções em cada etapa. Destaque as opções recomendadas.

### Feedback
Forneça feedback para cada ação do usuário. O feedback confirma que o sistema recebeu a ação e mostra o resultado.
*   **Tipos de Feedback:**
    *   **Visual:** Mudança de cor de um botão ao passar o mouse (`hover`) ou clicar (`active`), animações, spinners de carregamento.
    *   **Sonoro:** Sons de notificação (usar com moderação).
    *   **Tátil:** Vibração em dispositivos móveis.
