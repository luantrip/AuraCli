---
name: Software Architectural Patterns
description: Use this skill to understand, compare, and discuss common high-level software architectural patterns. It covers Monolithic, Microservices, Service-Oriented (SOA), Event-Driven, and Layered architectures, including their characteristics, pros, cons, and use cases. This is a foundational skill for a Senior Software Architect.
version: 1.0.0
author: Aura Core Team
---

# Guia de Referência: Padrões de Arquitetura de Software

Padrões de arquitetura são soluções reutilizáveis de alto nível para problemas comuns no design de software. A escolha do padrão correto é uma decisão fundamental que impacta a escalabilidade, manutenibilidade e o custo de um sistema.

## 1. Arquitetura Monolítica (Monolith)

### Descrição
A aplicação inteira é construída como uma única unidade. Todos os componentes (UI, lógica de negócios, acesso a dados) são acoplados e implantados juntos.

### Características
*   Base de código única.
*   Processo de build e implantação unificado.
*   Comunicação entre componentes é feita através de chamadas de função diretas dentro do mesmo processo.

### Vantagens (Prós)
*   **Simplicidade de Desenvolvimento:** Mais fácil de desenvolver, testar e depurar no início, pois tudo está em um só lugar.
*   **Performance:** Comunicação interna rápida (chamadas de função), sem a latência de rede.
*   **Implantação (Deploy) Simples:** Apenas um artefato a ser implantado.

### Desvantagens (Contras)
*   **Manutenibilidade:** A base de código pode se tornar massiva e difícil de entender (o "Big Ball of Mud").
*   **Escalabilidade:** Difícil escalar componentes individuais. A aplicação inteira precisa ser escalada, mesmo que apenas uma pequena parte dela esteja sob alta carga.
*   **Adoção de Tecnologia:** Fica "preso" a uma única stack tecnológica. Atualizar a tecnologia é um grande risco.
*   **Fragilidade:** Uma falha em um componente pode derrubar a aplicação inteira.

### Quando Usar
*   Pequenas aplicações e protótipos.
*   MVPs (Minimum Viable Products).
*   Quando a equipe é pequena e o domínio do problema ainda não é bem compreendido.

## 2. Arquitetura de Microsserviços (Microservices)

### Descrição
A aplicação é dividida em uma coleção de pequenos serviços independentes. Cada serviço é responsável por uma capacidade de negócio específica, possui sua própria base de código, seu próprio banco de dados (geralmente) e é implantado de forma independente.

### Características
*   Serviços pequenos, focados e fracamente acoplados.
*   Comunicação via rede (APIs REST, gRPC, filas de mensagens).
*   Propriedade descentralizada dos dados.

### Vantagens (Prós)
*   **Escalabilidade Independente:** Cada serviço pode ser escalado de forma independente.
*   **Flexibilidade Tecnológica:** Cada serviço pode ser escrito na linguagem ou framework mais apropriado para sua tarefa.
*   **Resiliência:** A falha de um serviço (se bem projetada) não derruba a aplicação inteira.
*   **Manutenibilidade:** Bases de código menores são mais fáceis de entender e manter.
*   **Implantação Independente:** Permite CI/CD rápido e independente para cada serviço.

### Desvantagens (Contras)
*   **Complexidade Operacional:** Requer automação robusta de implantação, monitoramento e orquestração (ex: Kubernetes).
*   **Complexidade de Comunicação:** A comunicação via rede introduz latência e a possibilidade de falhas.
*   **Consistência de Dados:** Manter a consistência dos dados entre diferentes serviços é um desafio (ex: Sagas).
*   **Testes Distribuídos:** Testar a interação entre múltiplos serviços é complexo.

### Quando Usar
*   Aplicações grandes e complexas.
*   Quando a escalabilidade e a implantação independente são requisitos críticos.
*   Em equipes grandes que podem trabalhar em paralelo em diferentes serviços.

## 3. Arquitetura Orientada a Serviços (Service-Oriented Architecture - SOA)

### Descrição
Um precursor dos microsserviços. A aplicação é composta por serviços, mas eles tendem a ser maiores (mais grosseiros) do que os microsserviços. Frequentemente, compartilham componentes, como um único banco de dados ou um Enterprise Service Bus (ESB) para comunicação.

### Diferenças para Microsserviços
*   **Escopo:** Serviços SOA são geralmente maiores e abrangem mais funcionalidades.
*   **Compartilhamento:** SOA tende a promover o reuso de componentes e pode compartilhar bancos de dados. Microsserviços visam o mínimo de compartilhamento.
*   **Comunicação:** SOA frequentemente depende de um ESB centralizado, enquanto microsserviços preferem canais de comunicação "burros" (APIs diretas, filas leves).

### Vantagens e Desvantagens
*   Um meio-termo entre Monolith e Microservices. Oferece melhor modularidade que um monólito, mas com menos complexidade operacional que microsserviços.

## 4. Arquitetura Orientada a Eventos (Event-Driven Architecture - EDA)

### Descrição
Os componentes do sistema reagem a "eventos". A comunicação é assíncrona. Um componente (o "produtor") publica um evento (ex: `PedidoCriado`) em um barramento de eventos (message broker), e outros componentes ("consumidores") se inscrevem nesses eventos e reagem a eles.

### Características
*   Componentes desacoplados. O produtor não sabe quem são os consumidores.
*   Comunicação assíncrona.
*   Baseada em um "message broker" (ex: RabbitMQ, Kafka, AWS SQS/SNS).

### Vantagens (Prós)
*   **Desacoplamento Extremo:** Produtores e consumidores são completamente independentes.
*   **Resiliência:** Se um consumidor falha, os eventos podem ser enfileirados e processados mais tarde.
*   **Escalabilidade:** Fácil adicionar novos consumidores para reagir aos mesmos eventos sem alterar os produtores.
*   **Responsividade:** Ideal para sistemas que precisam reagir a mudanças em tempo real.

### Desvantagens (Contras)
*   **Complexidade de Rastreamento:** Seguir o fluxo de uma lógica de negócios através de múltiplos eventos e consumidores pode ser difícil (requer boa observabilidade).
*   **Garantias de Entrega:** Lidar com entrega de mensagens (pelo menos uma vez, no máximo uma vez, exatamente uma vez) adiciona complexidade.
*   **Ordem dos Eventos:** Garantir a ordem correta do processamento de eventos pode ser um desafio.

### Quando Usar
*   Aplicações distribuídas e assíncronas.
*   Sistemas que precisam ser altamente resilientes e escaláveis.
*   Processamento de fluxos de dados (data streaming), IoT.

## 5. Arquitetura em Camadas (Layered Architecture)

### Descrição
Organiza o código em camadas horizontais, onde cada camada tem uma responsabilidade específica. Uma camada só pode se comunicar com a camada imediatamente abaixo dela. É um padrão muito comum em monólitos.

### Camadas Típicas
1.  **Camada de Apresentação (UI):** Responsável por toda a interação com o usuário.
2.  **Camada de Aplicação/Serviço:** Orquestra a lógica de negócios.
3.  **Camada de Domínio/Negócios:** Contém as regras de negócios centrais da aplicação.
4.  **Camada de Acesso a Dados/Persistência:** Responsável por se comunicar com o banco de dados.

### Vantagens (Prós)
*   **Separação de Responsabilidades (Separation of Concerns):** Bem organizada e fácil de entender.
*   **Manutenibilidade:** É possível alterar a UI sem impactar a lógica de negócios.

### Desvantagens (Contras)
*   Pode levar a um acoplamento indesejado se as camadas forem "puladas".
*   Em aplicações grandes, as camadas de negócios e de dados podem se tornar monolitos por si mesmas.
*   Não é inerentemente escalável (depende da arquitetura de implantação).

### Quando Usar
*   Aplicações de desktop padrão.
*   Pequenas aplicações web.
*   Como um ponto de partida para a organização interna de um monólito.
