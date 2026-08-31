"""
Testes Unitários para Sistema de Agentes do Aura CLI.

Este módulo contém testes unitários que verificam o funcionamento individual
de componentes do sistema de agentes, incluindo AgentBase, AgentOrchestrator
e AgentMemory. Testa funcionalidades isoladas sem dependências externas.

Componentes Testados:
    - AgentBase: Classe base abstrata para todos os agentes
    - AgentOrchestrator: Orquestrador de múltiplos agentes
    - AgentMemory: Sistema de memória persistente para agentes

Cenários de Teste:
    - Inicialização: Criação de agentes com parâmetros corretos
    - Adição de Tarefas: Adição de tarefas à fila do agente
    - Execução de Tarefas: Execução de tarefas individuais
    - Registro de Agentes: Registro no orquestrador
    - Distribuição de Tarefas: Distribuição de tarefas para agentes
    - Armazenamento de Memória: Armazenamento e recuperação de memórias
    - TTL de Memória: Expiração de memórias por tempo

Validações:
    - Agentes inicializam com estado correto
    - Tarefas são adicionadas corretamente
    - Tarefas são executadas e retornam resultados
    - Orquestrador gerencia agentes adequadamente
    - Memórias são armazenadas e recuperadas
    - TTL funciona corretamente

Estrutura de Testes:
    - TestAgentBase: Testes da classe base
    - TestAgentOrchestrator: Testes do orquestrador
    - TestAgentMemory: Testes do sistema de memória

MockAgent:
    Classe auxiliar que implementa AgentBase:
    - Retorna valores controlados
    - Rastreia tarefas executadas
    - Fornece ferramentas mock

AgentMemory:
    Sistema de memória persistente:
    - Armazenamento por agente e chave
    - Suporte a TTL (Time To Live)
    - Contexto adicional para memórias
    - Limpeza automática de expiradas

Exemplo de Uso:
    ```python
    def test_agent():
        agent = MockAgent("test_1", "Test", "Test")
        task_id = agent.add_task("Test task", priority=1)
        result = agent.execute_next_task()
        assert result == "Executed: Test task"
    ```

Dependências:
    - pytest: Framework de testes
    - unittest.mock: Para mocking
    - agent_base: Sistema de agentes base
    - agent_orchestrator: Sistema de orquestração
    - agent_memory: Sistema de memória
"""

from aura_cli.core.agents.agent_base import AgentBase, AgentStatus, AgentTask
from aura_cli.core.agents.agent_memory import AgentMemory
from aura_cli.core.agents.agent_orchestrator import (
    AgentOrchestrator,
    OrchestrationStrategy,
)


class MockAgent(AgentBase):
    """Agente mock para testes."""

    def _execute_task(self, task: AgentTask) -> any:
        return f"Executed: {task.description}"

    def _get_available_tools(self) -> list:
        return [{"name": "test_tool", "description": "Test"}]


class TestAgentBase:
    """Testes para AgentBase."""

    def test_agent_initialization(self):
        """Testa inicialização de agente."""
        agent = MockAgent(agent_id="test_1", name="Test Agent", description="Test")

        assert agent.agent_id == "test_1"
        assert agent.name == "Test Agent"
        assert agent.status == AgentStatus.IDLE

    def test_add_task(self):
        """Testa adição de tarefa."""
        agent = MockAgent("test_1", "Test", "Test")

        task_id = agent.add_task("Test task", priority=1)

        assert len(agent.task_queue) == 1
        assert agent.task_queue[0].description == "Test task"
        assert task_id is not None

    def test_execute_task(self):
        """Testa execução de tarefa."""
        agent = MockAgent("test_1", "Test", "Test")

        task = AgentTask(id="task_1", description="Test task", priority=1)

        # Adiciona à fila primeiro
        agent.task_queue.append(task)
        result = agent.execute_next_task()

        assert result == "Executed: Test task"
        assert agent.status == AgentStatus.IDLE or agent.status == AgentStatus.COMPLETED


class TestAgentOrchestrator:
    """Testes para AgentOrchestrator."""

    def test_orchestrator_initialization(self):
        """Testa inicialização do orquestrador."""
        orchestrator = AgentOrchestrator()

        assert len(orchestrator.agents) == 0
        assert orchestrator.strategy is not None
        assert isinstance(orchestrator.strategy, OrchestrationStrategy)

    def test_register_agent(self):
        """Testa registro de agente."""
        orchestrator = AgentOrchestrator()
        agent = MockAgent("test_1", "Test", "Test")

        orchestrator.register_agent(agent)

        assert "test_1" in orchestrator.agents
        assert orchestrator.agents["test_1"] == agent

    def test_execute_task_sequential(self):
        """Testa execução sequencial."""
        orchestrator = AgentOrchestrator()
        agent = MockAgent("test_1", "Test", "Test")
        orchestrator.register_agent(agent)

        # Distribui tarefa usando distribute_task
        task_id = orchestrator.distribute_task(
            task_description="Test", agent_id="test_1", priority=1
        )

        # Executa a tarefa do agente
        result = agent.execute_next_task()

        assert result == "Executed: Test"
        assert task_id is not None

    def test_execute_all_agents_parallel_respects_agent_queue_rules(self):
        """Execução paralela deve usar execute_next_task e respeitar dependências."""
        orchestrator = AgentOrchestrator(
            strategy=OrchestrationStrategy(parallel=True, max_concurrent=1)
        )
        agent = MockAgent("test_1", "Test", "Test")
        orchestrator.register_agent(agent)

        first_task_id = agent.add_task(
            "Blocked task", priority=10, dependencies=["missing"]
        )
        second_task_id = agent.add_task("Runnable task", priority=5)

        results = orchestrator.execute_all_agents(max_iterations=3)

        assert results["tasks_completed"] == 1
        assert agent.completed_tasks[0].id == second_task_id
        assert agent.task_queue[0].id == first_task_id


class TestAgentMemory:
    """Testes para AgentMemory."""

    def test_memory_initialization(self, temp_dir):
        """Testa inicialização de memória."""
        # Usa diretório temporário para evitar persistência entre testes
        storage_path = temp_dir / "memory"
        memory = AgentMemory(storage_path=str(storage_path))

        assert len(memory.memories) == 0
        assert memory.storage_path is not None

    def test_store_and_retrieve(self, temp_dir):
        """Testa armazenamento e recuperação."""
        storage_path = temp_dir / "memory"
        memory = AgentMemory(storage_path=str(storage_path))

        memory.store("test_agent", "key1", "value1", context={"type": "test"})

        entries = memory.retrieve("test_agent", key="key1")

        assert len(entries) > 0
        assert entries[0].value == "value1"
        assert entries[0].context.get("type") == "test"

    def test_ttl_expiration(self, temp_dir):
        """Testa expiração por TTL."""
        import time

        storage_path = temp_dir / "memory"
        memory = AgentMemory(storage_path=str(storage_path))

        memory.store("test_agent", "key1", "value1", ttl=1)  # 1 segundo

        entries = memory.retrieve("test_agent", key="key1")
        assert len(entries) > 0

        time.sleep(1.1)

        entries = memory.retrieve("test_agent", key="key1")
        assert len(entries) == 0  # Expirou
