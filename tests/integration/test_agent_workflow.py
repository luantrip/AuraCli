"""
Testes de Integração para Workflows de Agentes do Aura CLI.

Este módulo contém testes de integração que verificam o funcionamento completo
do sistema de workflows de agentes, incluindo execução sequencial, dependências
entre steps, e coordenação entre múltiplos agentes através do AgentOrchestrator.

Componentes Testados:
    - AgentOrchestrator: Orquestração de múltiplos agentes
    - Workflow: Definição de workflows multi-step
    - WorkflowStep: Steps individuais de um workflow
    - WorkflowExecutor: Execução de workflows completos
    - AgentBase: Interface base para agentes

MockAgent:
    Classe auxiliar que implementa AgentBase para testes:
    - Permite controlar valores de retorno
    - Rastreia tarefas executadas
    - Fornece ferramentas mock para testes

Cenários de Teste:
    - Execução Simples: Workflow com múltiplos steps executados sequencialmente
    - Dependências: Workflow onde steps dependem de steps anteriores
    - Múltiplos Agentes: Coordenação entre diferentes agentes em um workflow

Validações:
    - Verifica sucesso da execução do workflow
    - Valida que todos os steps foram executados
    - Confirma ordem de execução baseada em dependências
    - Verifica que agentes receberam e executaram tarefas corretas

Exemplo de Uso:
    ```python
    def test_workflow():
        orchestrator = AgentOrchestrator()
        agent = MockAgent("agent1", "Agent 1")
        orchestrator.register_agent(agent)

        workflow = Workflow(...)
        executor = WorkflowExecutor(orchestrator)
        results = executor.execute_workflow(workflow)

        assert results["success"]
    ```

Dependências:
    - pytest: Framework de testes
    - AgentOrchestrator: Sistema de orquestração
    - Workflow: Sistema de workflows
"""

from aura_cli.core.agents.agent_base import AgentBase, AgentTask
from aura_cli.core.agents.agent_orchestrator import (
    AgentOrchestrator,
    OrchestrationStrategy,
)
from aura_cli.core.agents.agent_workflow import Workflow, WorkflowExecutor


class MockAgent(AgentBase):
    """Agente mock para testes."""

    def __init__(self, agent_id, name, return_value="success"):
        super().__init__(agent_id, name, f"Mock agent {name}")
        self.return_value = return_value
        self.executed_tasks = []

    def _execute_task(self, task: AgentTask) -> any:
        self.executed_tasks.append(task.id)
        return self.return_value

    def _get_available_tools(self) -> list:
        return [{"name": "mock_tool"}]


class TrackingAgent(AgentBase):
    """Agent that tracks concurrent executions and received parameters."""

    def __init__(self, agent_id, name, tracker, delay=0.05):
        super().__init__(agent_id, name, f"Tracking agent {name}")
        self.tracker = tracker
        self.delay = delay
        self.last_parameters = None

    def _execute_task(self, task: AgentTask) -> any:
        import time

        self.last_parameters = task.parameters
        with self.tracker["lock"]:
            self.tracker["current"] += 1
            self.tracker["peak"] = max(self.tracker["peak"], self.tracker["current"])
            self.tracker["per_agent_peak"][self.agent_id] = max(
                self.tracker["per_agent_peak"].get(self.agent_id, 0),
                self.tracker["current_by_agent"].get(self.agent_id, 0) + 1,
            )
            self.tracker["current_by_agent"][self.agent_id] = (
                self.tracker["current_by_agent"].get(self.agent_id, 0) + 1
            )

        try:
            time.sleep(self.delay)
            return f"tracked:{task.description}"
        finally:
            with self.tracker["lock"]:
                self.tracker["current"] -= 1
                self.tracker["current_by_agent"][self.agent_id] -= 1

    def _get_available_tools(self) -> list:
        return [{"name": "tracking_tool"}]


class TestAgentWorkflow:
    """Testes de integração para workflows."""

    def test_simple_workflow_execution(self):
        """Testa execução de workflow simples."""
        orchestrator = AgentOrchestrator()

        agent1 = MockAgent("agent1", "Agent 1")
        agent2 = MockAgent("agent2", "Agent 2")

        orchestrator.register_agent(agent1)
        orchestrator.register_agent(agent2)

        workflow = Workflow(
            workflow_id="wf1",
            name="Test Workflow",
            description="Test workflow description",
        )

        workflow.add_step(
            step_id="step1", name="Step 1", agent_id="agent1", task_description="Task 1"
        )

        workflow.add_step(
            step_id="step2", name="Step 2", agent_id="agent2", task_description="Task 2"
        )

        executor = WorkflowExecutor(orchestrator)
        results = executor.execute_workflow(workflow)

        assert results["status"] == "completed"
        assert "step1" in results["steps_results"]
        assert "step2" in results["steps_results"]
        assert len(agent1.executed_tasks) == 1
        assert len(agent2.executed_tasks) == 1

    def test_workflow_with_dependencies(self):
        """Testa workflow com dependências."""
        orchestrator = AgentOrchestrator()

        agent1 = MockAgent("agent1", "Agent 1")
        orchestrator.register_agent(agent1)

        workflow = Workflow(
            workflow_id="wf2",
            name="Dependent Workflow",
            description="Workflow with dependencies",
        )

        workflow.add_step(
            step_id="step1", name="Step 1", agent_id="agent1", task_description="Task 1"
        )

        workflow.add_step(
            step_id="step2",
            name="Step 2",
            agent_id="agent1",
            task_description="Task 2",
            dependencies=["step1"],
        )

        executor = WorkflowExecutor(orchestrator)
        results = executor.execute_workflow(workflow)

        assert results["status"] == "completed"
        # step2 deve executar após step1
        assert len(agent1.executed_tasks) == 2

    def test_parallel_workflow_respects_max_concurrent(self):
        """Passos independentes devem usar paralelismo real até o limite configurado."""
        import threading

        tracker = {
            "lock": threading.Lock(),
            "current": 0,
            "peak": 0,
            "current_by_agent": {},
            "per_agent_peak": {},
        }
        orchestrator = AgentOrchestrator(
            strategy=OrchestrationStrategy(parallel=True, max_concurrent=2)
        )

        orchestrator.register_agent(TrackingAgent("agent1", "Agent 1", tracker))
        orchestrator.register_agent(TrackingAgent("agent2", "Agent 2", tracker))
        orchestrator.register_agent(TrackingAgent("agent3", "Agent 3", tracker))

        workflow = Workflow("wf_parallel", "Parallel Workflow", "Parallel test")
        workflow.add_step("step1", "Step 1", "agent1", "Task 1")
        workflow.add_step("step2", "Step 2", "agent2", "Task 2")
        workflow.add_step("step3", "Step 3", "agent3", "Task 3")

        executor = WorkflowExecutor(orchestrator)
        results = executor.execute_workflow(workflow)

        assert results["status"] == "completed"
        assert tracker["peak"] == 2

    def test_parallel_workflow_does_not_schedule_same_agent_twice_in_one_batch(self):
        """Mesmo em paralelo, um agente não deve executar dois passos simultâneos."""
        import threading

        tracker = {
            "lock": threading.Lock(),
            "current": 0,
            "peak": 0,
            "current_by_agent": {},
            "per_agent_peak": {},
        }
        orchestrator = AgentOrchestrator(
            strategy=OrchestrationStrategy(parallel=True, max_concurrent=3)
        )

        agent = TrackingAgent("agent1", "Agent 1", tracker)
        orchestrator.register_agent(agent)

        workflow = Workflow(
            "wf_same_agent", "Same Agent Workflow", "No double scheduling"
        )
        workflow.add_step("step1", "Step 1", "agent1", "Task 1")
        workflow.add_step("step2", "Step 2", "agent1", "Task 2")

        executor = WorkflowExecutor(orchestrator)
        results = executor.execute_workflow(workflow)

        assert results["status"] == "completed"
        assert tracker["per_agent_peak"]["agent1"] == 1

    def test_step_parameters_override_shared_workflow_context(self):
        """Parâmetros explícitos do passo devem sobrescrever contexto compartilhado."""
        import threading

        tracker = {
            "lock": threading.Lock(),
            "current": 0,
            "peak": 0,
            "current_by_agent": {},
            "per_agent_peak": {},
        }
        orchestrator = AgentOrchestrator()
        agent = TrackingAgent("agent1", "Agent 1", tracker, delay=0)
        orchestrator.register_agent(agent)

        workflow = Workflow("wf_context", "Context Workflow", "Context precedence")
        workflow.context["target"] = "from_context"
        workflow.add_step(
            "step1",
            "Step 1",
            "agent1",
            "Task 1",
            parameters={"target": "from_step", "extra": "value"},
        )

        executor = WorkflowExecutor(orchestrator)
        results = executor.execute_workflow(workflow)

        assert results["status"] == "completed"
        assert agent.last_parameters["target"] == "from_step"
        assert workflow.results["step1"] == "tracked:Task 1"
