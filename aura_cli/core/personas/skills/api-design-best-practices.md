---
name: API Design Best Practices (REST & GraphQL)
description: Use this skill to design, critique, and implement robust and developer-friendly APIs. It covers the principles of REST and GraphQL, endpoint design, status codes, versioning, authentication, and documentation. This is a core skill for Senior Engineers and Architects.
version: 1.0.0
author: Aura Core Team
---

# Guia de Referência: Melhores Práticas de Design de API

Este guia aborda os princípios e as melhores práticas para o design de APIs, com foco nos dois estilos arquiteturais mais populares: REST e GraphQL.

## 1. REST (Representational State Transfer)

REST é um estilo arquitetural para sistemas hipermídia distribuídos. APIs RESTful são organizadas em torno de **recursos** (substantivos) e das **operações** (verbos HTTP) que podem ser realizadas sobre eles.

### Princípios Chave do REST
*   **Cliente-Servidor:** Separação clara entre o cliente (que consome a API) e o servidor (que a expõe).
*   **Stateless:** Cada requisição do cliente para o servidor deve conter toda a informação necessária para o servidor entender e processar a requisição. O servidor não armazena estado da sessão do cliente.
*   **Cacheable:** As respostas devem ser definíveis como cacheáveis ou não-cacheáveis.
*   **Interface Uniforme:** Esta é a restrição mais importante e é composta por 4 sub-restrições:
    1.  **Identificação de Recursos:** Recursos são identificados por URIs (ex: `/users/123`).
    2.  **Manipulação de Recursos Através de Representações:** O cliente interage com uma representação do recurso (ex: JSON), não com o recurso em si.
    3.  **Mensagens Autodescritivas:** A resposta contém informação suficiente para o cliente entender como processá-la (ex: `Content-Type: application/json`).
    4.  **HATEOAS (Hypermedia as the Engine of Application State):** A resposta contém links para outras ações/recursos relacionados, permitindo que o cliente navegue na API.

### Melhores Práticas de Design REST

#### 1. Use Substantivos para Recursos, não Verbos
*   **Ruim:** `/getAllUsers`, `/createUser`
*   **Bom:** `/users` (para a coleção), `/users/123` (para um recurso específico)

#### 2. Use Verbos HTTP Corretamente
*   **`GET`:** Recuperar um recurso. É seguro e idempotente.
    *   `GET /users` -> Lista todos os usuários.
    *   `GET /users/123` -> Recupera o usuário com ID 123.
*   **`POST`:** Criar um novo recurso. Não é seguro nem idempotente.
    *   `POST /users` -> Cria um novo usuário.
*   **`PUT`:** Atualizar/substituir um recurso existente. É idempotente.
    *   `PUT /users/123` -> Substitui completamente os dados do usuário 123.
*   **`PATCH`:** Atualizar parcialmente um recurso existente. Não é necessariamente idempotente.
    *   `PATCH /users/123` -> Atualiza apenas um campo (ex: o email) do usuário 123.
*   **`DELETE`:** Remover um recurso. É idempotente.
    *   `DELETE /users/123` -> Remove o usuário 123.

#### 3. Use Códigos de Status HTTP Apropriados
*   **2xx (Sucesso):**
    *   `200 OK`: Requisição bem-sucedida.
    *   `201 Created`: Recurso criado com sucesso (resposta a um `POST`).
    *   `204 No Content`: Sucesso, mas não há conteúdo para retornar (resposta a um `DELETE`).
*   **4xx (Erro do Cliente):**
    *   `400 Bad Request`: Requisição malformada (ex: JSON inválido).
    *   `401 Unauthorized`: Autenticação necessária e falhou ou não foi fornecida.
    *   `403 Forbidden`: O cliente está autenticado, mas não tem permissão para acessar o recurso.
    *   `404 Not Found`: O recurso solicitado não existe.
*   **5xx (Erro do Servidor):**
    *   `500 Internal Server Error`: Um erro genérico no servidor.

#### 4. Suporte a Filtragem, Ordenação e Paginação
*   **Filtragem:** `GET /users?status=active`
*   **Ordenação:** `GET /users?sort=-created_at` (o `-` indica ordem decrescente)
*   **Paginação:** `GET /users?page=2&limit=50`

#### 5. Versionamento da API
É crucial para evitar quebrar clientes existentes quando você faz alterações.
*   **Via URI (comum):** `https://api.example.com/v1/users`
*   **Via Header (mais puro):** `Accept: application/vnd.example.api.v1+json`

## 2. GraphQL

GraphQL é uma linguagem de consulta para APIs e um runtime para executar essas consultas com seus dados existentes. Ele oferece uma abordagem diferente e mais flexível em comparação com o REST.

### Conceitos Chave do GraphQL
*   **Schema Fortemente Tipado:** O coração do GraphQL é um schema que define todos os tipos de dados e as operações (queries, mutations) disponíveis.
*   **Ponto de Extremidade Único (Single Endpoint):** Geralmente, todas as requisições (queries e mutations) são enviadas para um único endpoint (ex: `/graphql`).
*   **Cliente Decide o que Pedir:** O cliente especifica exatamente quais dados ele precisa, e a resposta contém apenas esses dados.

### Vantagens (Prós)
*   **Sem Over-fetching ou Under-fetching:** Resolve o principal problema do REST, onde ou você recebe mais dados do que precisa (over-fetching) ou precisa fazer múltiplas requisições para obter todos os dados (under-fetching).
*   **Schema e Tipagem Fortes:** A API é autodescritiva e menos propensa a erros.
*   **Desenvolvimento de Frontend Agilizado:** O frontend pode evoluir sem esperar por mudanças no backend, desde que os dados estejam disponíveis no schema.

### Desvantagens (Contras)
*   **Complexidade no Lado do Servidor:** Implementar um servidor GraphQL robusto (com resolvers, data loaders para evitar o problema N+1) é mais complexo do que uma API REST simples.
*   **Cache:** O cache HTTP não funciona da mesma forma, pois todas as requisições são `POST` para um único endpoint. O cache precisa ser implementado no lado do cliente.
*   **Monitoramento de Taxa (Rate Limiting):** Mais difícil de implementar, pois a "complexidade" de uma consulta pode variar muito.

### Exemplo de Consulta GraphQL

```graphql
query GetUserAndPosts {
  user(id: "123") {
    id
    name
    email
    posts(first: 5) {
      id
      title
      createdAt
    }
  }
}
```
*Nesta única requisição, o cliente pede os detalhes de um usuário e seus 5 posts mais recentes. Em REST, isso provavelmente exigiria duas requisições (`/users/123` e `/users/123/posts`).*

## 3. Quando Escolher REST vs. GraphQL?

| Fator                | Prefira REST                                       | Prefira GraphQL                                    |
| -------------------- | -------------------------------------------------- | -------------------------------------------------- |
| **Caso de Uso**      | APIs públicas simples, CRUD baseado em recursos.   | Aplicações complexas, mobile, frontends que iteram rapidamente. |
| **Clientes Diversos**| Quando os clientes e seus requisitos de dados são bem conhecidos. | Quando múltiplos clientes (web, mobile, IoT) consomem a mesma API com diferentes necessidades de dados. |
| **Performance**      | Bom, mas pode levar a múltiplas chamadas de rede.  | Excelente para reduzir o número de chamadas de rede. |
| **Simplicidade**     | Mais fácil de começar a construir no lado do servidor. | Mais fácil para o cliente consumir.                |
| **Controle de Dados**| O servidor define a estrutura da resposta.          | O cliente tem controle total sobre a estrutura da resposta. |
| **Cache**            | Utiliza o cache HTTP padrão de forma eficaz.       | Requer estratégias de cache mais complexas.        |

## 4. Melhores Práticas Gerais

*   **Documentação é Essencial:** Use ferramentas como Swagger/OpenAPI para REST ou as ferramentas de introspecção do GraphQL para gerar documentação interativa.
*   **Autenticação e Autorização:** Proteja suas APIs. Use padrões como OAuth 2.0. A autenticação verifica *quem* é o usuário, a autorização verifica *o que* ele pode fazer.
*   **Validação de Entrada:** Nunca confie nos dados que vêm do cliente. Valide tudo no lado do servidor.
