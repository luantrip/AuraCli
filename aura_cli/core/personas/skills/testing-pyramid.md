---
name: The Testing Pyramid
description: Use this skill to understand and explain the software testing pyramid. It covers the three main layers—Unit Tests, Integration Tests, and End-to-End (E2E) Tests—explaining the purpose, scope, speed, and cost of each. This is a foundational skill for ensuring software quality.
version: 1.0.0
author: Aura Core Team
---

# Guia de Referência: A Pirâmide de Testes

A Pirâmide de Testes é um modelo que ajuda a estruturar uma estratégia de testes automatizados saudável e sustentável. A ideia é ter muitos testes rápidos e de baixo nível na base, e um número menor de testes lentos e de alto nível no topo.

A pirâmide é dividida em três camadas principais (de baixo para cima): Testes Unitários, Testes de Integração e Testes de Ponta a Ponta (E2E).

## 1. Testes Unitários (Unit Tests) - A Base da Pirâmide

### Descrição
*   **O que testam:** A menor unidade de código de forma isolada. Geralmente, uma única função ou um método de uma classe.
*   **Escopo:** Mínimo. Todas as dependências externas (como banco de dados, chamadas de rede, sistema de arquivos) são substituídas por "dublês de teste" (Test Doubles), como **Mocks** ou **Stubs**.
*   **Objetivo:** Verificar se a lógica da unidade de código está correta.

### Características
*   **Velocidade:** Extremamente rápidos (milissegundos).
*   **Custo:** Muito baratos para escrever e manter.
*   **Quantidade:** A grande maioria dos testes em uma aplicação deve ser de unidade.
*   **Feedback:** Fornecem feedback preciso e imediato ao desenvolvedor. Se um teste unitário falha, você sabe exatamente qual função quebrou.

### Exemplo (Python com `pytest`)

```python
# Código a ser testado (ex: em um arquivo 'calculadora.py')
def somar(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Ambos os operandos devem ser números")
    return a + b


# Teste unitário (ex: em 'test_calculadora.py')
import pytest
from calculadora import somar


def test_somar_dois_numeros_positivos():
    # Testa o "caminho feliz"
    assert somar(2, 3) == 5


def test_somar_um_numero_negativo():
    assert somar(-5, 10) == 5


def test_somar_deve_lancar_excecao_para_nao_numeros():
    # Testa o tratamento de erro
    with pytest.raises(TypeError):
        somar("2", 3)
```

## 2. Testes de Integração (Integration Tests) - O Meio da Pirâmide

### Descrição
*   **O que testam:** A interação entre duas ou mais unidades de código. Verificam se os módulos, quando combinados, funcionam juntos como esperado.
*   **Escopo:** Médio. Podem envolver a comunicação entre seu código e um sistema externo real, como um banco de dados (geralmente em um contêiner de teste) ou uma outra API da sua própria aplicação.
*   **Objetivo:** Encontrar falhas nas "costuras" entre os componentes.

### Características
*   **Velocidade:** Mais lentos que os testes unitários (segundos).
*   **Custo:** Mais caros para escrever e manter, pois exigem um ambiente mais complexo (ex: iniciar um banco de dados).
*   **Quantidade:** Menos numerosos que os testes unitários.
*   **Feedback:** Menos preciso que os testes unitários. Se um teste de integração falha, o problema está na interação entre os componentes, o que pode exigir mais investigação.

### Exemplo (Python com `pytest` e uma API web)

```python
# Código da API (usando FastAPI)
from fastapi import FastAPI

app = FastAPI()


@app.post("/users/")
def create_user(user: dict):
    # (Aqui haveria a lógica para salvar o usuário no banco de dados)
    user_id = 1
    return {"id": user_id, **user}


# Teste de integração (testando o endpoint da API)
from fastapi.testclient import TestClient

client = TestClient(app)


def test_create_user_endpoint():
    response = client.post(
        "/users/",
        json={"name": "Aura", "email": "aura@cli.ai"},
    )
    # Verifica se o endpoint respondeu corretamente
    assert response.status_code == 200
    data = response.json()
    # Verifica se a resposta contém os dados esperados
    assert data["name"] == "Aura"
    assert "id" in data
```

## 3. Testes de Ponta a Ponta (End-to-End / E2E) - O Topo da Pirâmide

### Descrição
*   **O que testam:** O fluxo completo da aplicação, da perspectiva do usuário. Simulam o comportamento real do usuário na interface (seja uma TUI, uma UI web ou uma CLI).
*   **Escopo:** Máximo. Envolvem todo o sistema: frontend, backend, banco de dados, APIs externas, etc.
*   **Objetivo:** Garantir que a aplicação como um todo funcione e entregue o valor de negócio esperado.

### Características
*   **Velocidade:** Muito lentos (de vários segundos a minutos).
*   **Custo:** Extremamente caros para escrever, manter e executar. São frágeis e podem quebrar devido a pequenas mudanças na UI.
*   **Quantidade:** Deve haver apenas um pequeno número de testes E2E, focados nos fluxos de usuário mais críticos ("happy paths").
*   **Feedback:** Muito impreciso. Se um teste E2E falha, pode haver um problema em qualquer lugar do sistema.

### Exemplo (Conceitual, usando Selenium para web)

```python
from selenium import webdriver


def test_login_e_logout_flow():
    driver = webdriver.Chrome()
    driver.get("https://minha-app.com/login")

    # Encontra os campos e o botão
    username_input = driver.find_element_by_id("username")
    password_input = driver.find_element_by_id("password")
    submit_button = driver.find_element_by_tag_name("button")

    # Preenche e submete o formulário
    username_input.send_keys("usuario_teste")
    password_input.send_keys("senha_segura")
    submit_button.click()

    # Verifica se o usuário foi redirecionado para o dashboard
    assert "dashboard" in driver.current_url

    # Encontra e clica no botão de logout
    logout_button = driver.find_element_by_id("logout")
    logout_button.click()

    # Verifica se o usuário retornou para a página de login
    assert "login" in driver.current_url

    driver.quit()
```

### Resumo da Estratégia

*   **Invista na base:** Escreva muitos testes unitários. Eles são rápidos, estáveis e dão o melhor retorno sobre o investimento.
*   **Use testes de integração com moderação:** Use-os para garantir que as partes importantes do seu sistema se comunicam corretamente.
*   **Seja muito seletivo com testes E2E:** Use-os apenas para os fluxos de usuário mais críticos que garantem que seu negócio funciona.
