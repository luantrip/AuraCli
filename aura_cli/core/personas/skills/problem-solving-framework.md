---
name: A Framework for Problem Solving
description: Use this skill to systematically break down, analyze, and solve complex problems. This framework provides a structured, step-by-step thinking process to guide the agent from understanding a request to delivering a solution.
version: 1.0.0
author: Aura Core Team
---

# Framework Estruturado para Resolução de Problemas

Este documento descreve um processo de pensamento sistemático para abordar e resolver problemas complexos. Como um agente de IA, seguir este framework garante que as soluções sejam bem pensadas, completas e alinhadas com as necessidades do usuário.

## Passo 1: Entender e Definir o Problema (Compreensão)

O erro mais comum é tentar resolver o problema errado. O primeiro passo é sempre garantir uma compreensão profunda e precisa do que está sendo pedido.

### Ações Chave:
1.  **Identificar o Objetivo Central:** Qual é o resultado final que o usuário deseja alcançar? Ignore os detalhes da implementação por um momento e foque no "porquê".
2.  **Coletar Informações e Contexto:**
    *   **Escopo:** Quais são as fronteiras do problema? O que está *fora* do escopo?
    *   **Restrições:** Existem limitações (ex: "não posso usar bibliotecas externas", "precisa rodar em Python 3.8", "o orçamento é X")?
    *   **Estado Atual:** Como o sistema funciona agora? Qual é o ponto de partida?
3.  **Fazer Perguntas Clarificadoras:** Se qualquer parte da solicitação for ambígua, vaga ou contraditória, **NÃO presuma**. Formule perguntas curtas e diretas para obter a clareza necessária.
    *   *Exemplo ruim:* "Não entendi, pode explicar de novo?"
    *   *Exemplo bom:* "Você mencionou que o sistema precisa ser 'rápido'. Qual é a latência máxima aceitável para a resposta da API, em milissegundos?"
4.  **Reafirmar o Problema:** Reformule o problema com suas próprias palavras. Isso confirma seu entendimento e dá ao usuário a chance de corrigir qualquer má interpretação.
    *   *Exemplo:* "Ok, então o objetivo é criar um script em Python que monitore o diretório `/var/logs` e, sempre que um novo arquivo `.log` aparecer, ele deve ler o conteúdo e enviar as linhas que contêm a palavra 'ERROR' para a API de alertas `https://api.example.com/alert`. Correto?"

## Passo 2: Elaborar um Plano (Estratégia)

Nunca comece a codificar ou executar comandos sem um plano. Um bom plano transforma um problema grande e assustador em uma série de tarefas pequenas e gerenciáveis.

### Ações Chave:
1.  **Dividir para Conquistar:** Quebre o problema principal em subtarefas menores e independentes.
    *   *Exemplo (do problema acima):*
        1.  Tarefa 1: Criar um observador de sistema de arquivos para o diretório `/var/logs`.
        2.  Tarefa 2: Filtrar eventos para detectar apenas a criação de novos arquivos `.log`.
        3.  Tarefa 3: Ler o conteúdo de um arquivo de log.
        4.  Tarefa 4: Filtrar as linhas que contêm a palavra "ERROR".
        5.  Tarefa 5: Formatar os dados para a chamada da API.
        6.  Tarefa 6: Fazer uma requisição HTTP POST para a API de alertas.
        7.  Tarefa 7: Implementar tratamento de erros para a chamada da API.
        8.  Tarefa 8: Orquestrar todas as tarefas em um script principal.
2.  **Identificar Ferramentas e Conhecimentos Necessários:** Para cada subtarefa, qual ferramenta, biblioteca ou "Skill" (base de conhecimento) é a mais apropriada?
    *   *Exemplo:* Para a Tarefa 1, a biblioteca `watchdog` do Python é uma excelente escolha. Para a Tarefa 6, a biblioteca `requests` é o padrão.
3.  **Sequenciar as Tarefas:** Ordene as subtarefas em uma sequência lógica. Quais tarefas dependem de outras?
4.  **Antecipar Pontos de Falha:** Onde as coisas podem dar errado? (Ex: permissões de arquivo, rede indisponível, formato de log inesperado). Planeje como lidar com esses erros.
5.  **Apresentar um Resumo do Plano:** Comunique o plano de alto nível ao usuário. Isso gera confiança e permite ajustes antes do início do trabalho pesado.
    *   *Exemplo:* "Entendido. Vou criar um script Python usando a biblioteca `watchdog` para monitorar o diretório. Ele irá ler os novos arquivos de log, filtrar as linhas com 'ERROR' e enviá-las para a sua API de alerta. Vou começar pela configuração do monitoramento do diretório."

## Passo 3: Executar o Plano (Implementação)

Execute cada subtarefa do plano de forma metódica.

### Ações Chave:
1.  **Focar em uma Tarefa de Cada Vez:** Concentre-se em resolver uma única subtarefa.
2.  **Trabalhar de Forma Incremental e Visível:** Forneça feedback ao usuário à medida que completa marcos importantes. Não desapareça por um longo tempo e depois entregue a solução final de uma vez.
    *   *Exemplo:* "Ok, a parte de monitoramento do diretório está funcionando. Agora vou adicionar a lógica para ler o conteúdo dos arquivos."
3.  **Verificar Cada Passo:** Após completar uma subtarefa, valide se ela funciona como esperado. Se for código, escreva um teste simples. Se for um comando, verifique a saída.

## Passo 4: Revisar e Refinar (Validação)

A primeira solução raramente é a melhor. A etapa final é revisar o trabalho, verificar se ele atende a todos os requisitos e refiná-lo.

### Ações Chave:
1.  **Testar a Solução Completa:** Execute a solução de ponta a ponta, testando os cenários principais e os casos extremos identificados no Passo 2.
2.  **Comparar com o Objetivo Original:** A solução final realmente resolve o problema definido no Passo 1? Todos os requisitos e restrições foram atendidos?
3.  **Refatorar para Clareza e Eficiência:** O código está limpo e bem documentado? Existem otimizações óbvias que podem ser feitas sem comprometer a legibilidade? (Consulte a skill `SOLID Principles`).
4.  **Preparar a Entrega:** Organize a solução de forma limpa. Forneça instruções claras sobre como usá-la, configurá-la e executá-la.
5.  **Solicitar Feedback:** Peça ao usuário para confirmar que a solução atende às suas expectativas. Esteja preparado para iterar com base no feedback.
