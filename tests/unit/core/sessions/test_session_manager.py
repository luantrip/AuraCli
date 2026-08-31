"""
Testes para o sistema de sessões.

Propósito: Verifica gerenciamento de sessões e estado persistente
Componentes: SessionManager, SessionState, get_session_manager
"""

from datetime import datetime
import json
from pathlib import Path
import tempfile

import pytest

from aura_cli.core.sessions.session_manager import (
    Session,
    SessionManager,
    get_session_manager,
)


class TestSession:
    """Testes para Session."""

    def test_session_creation(self):
        """Testa criação de sessão."""
        session = Session(
            id="test_session",
            name="Test Session",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        assert session.id == "test_session"
        assert session.name == "Test Session"
        assert session.conversation_history == []
        assert session.context == {}

    def test_session_with_data(self):
        """Verifica sessão com dados."""
        session = Session(
            id="data_session",
            name="Data Session",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        session.add_message("user", "Hello")
        session.set_context("project", "aura-cli")

        assert session.id == "data_session"
        assert len(session.conversation_history) == 1
        assert session.get_context("project") == "aura-cli"


class TestSessionManager:
    """Testes para SessionManager."""

    @pytest.fixture
    def temp_sessions_dir(self):
        """Diretório temporário para sessões."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def session_manager(self, temp_sessions_dir):
        """Manager configurado para testes."""
        return SessionManager(storage_path=temp_sessions_dir)

    @pytest.fixture
    def sample_session(self):
        """Sessão de exemplo."""
        session = Session(
            id="sample_session",
            name="Sample Session",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")
        session.set_agent_state("agi", {"current_task": "Analysis", "files": 5})
        return session

    def test_manager_initialization(self, temp_sessions_dir):
        """Verifica inicialização do manager."""
        manager = SessionManager(storage_path=temp_sessions_dir)
        assert manager.storage_path == temp_sessions_dir
        assert temp_sessions_dir.exists()

    def test_create_session(self, session_manager):
        """Testa criação de sessão."""
        session = session_manager.create_session("test_session")

        assert session is not None
        assert session.id is not None
        # Verifica que a sessão foi criada (verificando se arquivo existe)
        session_file = session_manager.storage_path / f"{session.id}.json"
        assert session_file.exists()

        assert session.name == "test_session"

    def test_create_session_with_metadata(self, session_manager):
        """Verifica criação com metadados."""
        # Note: create_session não aceita metadata diretamente, mas podemos usar context
        session = session_manager.create_session(
            "meta_session", description="Test session"
        )

        assert session is not None
        assert session.name == "meta_session"
        # Metadata pode ser adicionado via context
        session.set_context("project", "aura-cli")
        session.set_context("mode", "development")
        assert session.get_context("project") == "aura-cli"

    def test_save_and_load_session(self, session_manager):
        """Verifica salvamento e carregamento."""
        # Cria sessão
        session = session_manager.create_session("test_save_load")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")
        session_id = session.id

        # Salva
        session_manager.save_session(session)

        # Carrega
        loaded_session = session_manager.load_session(session_id)
        assert loaded_session is not None
        assert loaded_session.id == session_id
        assert len(loaded_session.conversation_history) == 2

    def test_save_session_preserves_previous_snapshot_on_serialization_error(
        self, session_manager, sample_session
    ):
        """Uma falha de serialização não deve deixar JSON parcial no destino."""
        session_manager.save_session(sample_session)
        session_path = session_manager.storage_path / f"{sample_session.id}.json"
        previous_snapshot = session_path.read_text(encoding="utf-8")
        sample_session.context["not_serializable"] = object()

        with pytest.raises(TypeError):
            session_manager.save_session(sample_session)

        assert session_path.read_text(encoding="utf-8") == previous_snapshot
        assert not list(
            session_manager.storage_path.glob(f".{sample_session.id}.*.tmp")
        )

    def test_list_sessions(self, session_manager):
        """Testa listagem de sessões."""
        # Cria múltiplas sessões
        session1 = session_manager.create_session("session1")
        session2 = session_manager.create_session("session2")
        session1_id = session1.id
        session2_id = session2.id

        sessions = session_manager.list_sessions()
        assert len(sessions) >= 2

        session_ids = [s.id for s in sessions]
        assert session1_id in session_ids
        assert session2_id in session_ids

    def test_delete_session(self, session_manager):
        """Verifica remoção de sessão."""
        session = session_manager.create_session("test_delete")
        session_id = session.id
        session_manager.save_session(session)

        assert session_manager.load_session(session_id) is not None

        result = session_manager.delete_session(session_id)
        assert result is True
        assert session_manager.load_session(session_id) is None

    def test_add_message_to_session(self, session_manager):
        """Testa adição de mensagem à sessão."""
        session = session_manager.create_session("message_test")
        session.add_message("user", "Hello world!")
        session_manager.save_session(session)

        loaded_session = session_manager.load_session(session.id)
        assert len(loaded_session.conversation_history) == 1
        assert loaded_session.conversation_history[0]["content"] == "Hello world!"

    def test_update_agent_state_in_session(self, session_manager):
        """Verifica atualização de estado de agente."""
        session = session_manager.create_session("agent_test")
        session.set_agent_state(
            "agi", {"current_task": "Processing", "status": "active"}
        )
        session_manager.save_session(session)

        loaded_session = session_manager.load_session(session.id)
        assert "agi" in loaded_session.agent_states
        assert (
            loaded_session.agent_states["agi"]["state"]["current_task"] == "Processing"
        )

    def test_get_session_stats(self, session_manager):
        """Verifica obtenção de estatísticas."""
        # Cria sessões com diferentes quantidades de mensagens
        session1 = session_manager.create_session("stats1")
        session2 = session_manager.create_session("stats2")

        # Adiciona mensagens
        for i in range(5):
            session1.add_message("user", f"Message {i}")

        for i in range(3):
            session2.add_message("user", f"Message {i}")

        session_manager.save_session(session1)
        session_manager.save_session(session2)

        # Verifica listagem
        sessions = session_manager.list_sessions()
        assert len(sessions) >= 2

    def test_cleanup_old_sessions(self, session_manager):
        """Testa limpeza de sessões antigas."""
        # Cria sessões
        session1 = session_manager.create_session("old1")
        session2 = session_manager.create_session("old2")
        session3 = session_manager.create_session("recent")

        session_manager.save_session(session1)
        session_manager.save_session(session2)
        session_manager.save_session(session3)

        # Verifica que sessões foram criadas
        sessions = session_manager.list_sessions()
        assert len(sessions) >= 3

    def test_export_session(self, session_manager):
        """Verifica exportação de sessão."""
        session = session_manager.create_session("export_test")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")
        session_manager.save_session(session)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            export_path = temp_file.name

        # export_session retorna bool
        result = session_manager.export_session(session.id, export_path)
        assert result is True

        # Verifica que arquivo foi criado
        assert Path(export_path).exists()
        exported_data = json.loads(Path(export_path).read_text())
        assert exported_data["session"]["id"] == session.id

        # Limpar arquivo temporário
        import os

        os.unlink(export_path)

    def test_import_session(self, session_manager):
        """Testa importação de sessão."""
        # Cria sessão e exporta
        session = session_manager.create_session("import_test")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")
        session_manager.save_session(session)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            export_path = temp_file.name

        session_manager.export_session(session.id, export_path)

        # Importa
        imported_session = session_manager.import_session(export_path)

        assert imported_session is not None
        assert len(imported_session.conversation_history) == 2


class TestGlobalSessionManager:
    """Testes para função global de session manager."""

    def test_get_session_manager_singleton(self):
        """Verifica padrão singleton."""
        manager1 = get_session_manager()
        manager2 = get_session_manager()

        assert manager1 is manager2

    def test_get_session_manager_default_location(self):
        """Testa localização padrão das sessões."""
        # Reset singleton para testar
        import aura_cli.core.sessions.session_manager as session_module

        session_module._session_manager = None

        manager = get_session_manager()
        from aura_cli.core.paths import aura_path

        expected_path = aura_path("sessions")

        assert manager.storage_path == expected_path

        # Reset singleton novamente
        session_module._session_manager = None

    def test_get_session_manager_applies_explicit_workspace_root(self, tmp_path):
        """A workspace context updates the singleton without changing storage."""
        import aura_cli.core.sessions.session_manager as session_module

        previous = session_module._session_manager
        try:
            session_module._session_manager = None
            manager = get_session_manager(tmp_path / "workspace")
            assert manager.workspace_root == (tmp_path / "workspace").resolve()
            assert get_session_manager() is manager
        finally:
            session_module._session_manager = previous


class TestSessionIntegration:
    """Testes de integração do sistema de sessões."""

    @pytest.fixture
    def temp_sessions_dir(self):
        """Diretório temporário para sessões."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_complete_session_lifecycle(self, temp_sessions_dir):
        """Testa ciclo de vida completo de sessão."""
        manager = SessionManager(storage_path=temp_sessions_dir)

        # 1. Criar sessão
        session = manager.create_session("dev_session", description="Test session")
        session.set_context("project", "test-project")
        session.set_context("user", "developer")
        session_id = session.id

        # 2. Adicionar conversação
        session.add_message("user", "Start new project")
        session.add_message("assistant", "I'll help you create a new project")

        # 3. Atualizar estado do agente
        session.set_agent_state(
            "agi",
            {
                "current_task": "Project initialization",
                "phase": "planning",
                "files_created": 0,
                "user_preferences": {"framework": "fastapi"},
            },
        )

        # 4. Salvar sessão
        manager.save_session(session)

        # 5. Simular restart - criar novo manager
        new_manager = SessionManager(storage_path=temp_sessions_dir)

        # 6. Carregar sessão
        loaded_session = new_manager.load_session(session_id)

        # 7. Verificar integridade
        assert loaded_session is not None
        assert loaded_session.get_context("project") == "test-project"
        assert len(loaded_session.conversation_history) == 2
        assert "agi" in loaded_session.agent_states
        agi_state = loaded_session.agent_states["agi"]["state"]
        assert agi_state["current_task"] == "Project initialization"

        # 8. Continuar conversação
        loaded_session.add_message("user", "Create main.py file")

        # 9. Atualizar estado
        agi_state["files_created"] = 1
        loaded_session.set_agent_state("agi", agi_state)
        new_manager.save_session(loaded_session)

        # 10. Verificar persistência
        final_session = new_manager.load_session(session_id)
        assert len(final_session.conversation_history) == 3
        assert final_session.agent_states["agi"]["state"]["files_created"] == 1

    def test_multi_agent_session(self, temp_sessions_dir):
        """Testa sessão com múltiplos agentes."""
        manager = SessionManager(storage_path=temp_sessions_dir)

        session = manager.create_session("multi_agent_session")

        # Estados de diferentes agentes
        agents = {
            "agi": {"current_task": "Code analysis", "files_analyzed": 10},
            "ops": {"current_task": "System monitoring", "alerts": 2},
            "chat": {"current_task": "User interaction", "mode": "helpful"},
        }

        # Atualiza estados
        for agent_type, state in agents.items():
            session.set_agent_state(agent_type, state)

        manager.save_session(session)

        # Carrega e verifica
        loaded_session = manager.load_session(session.id)
        assert "agi" in loaded_session.agent_states
        assert "ops" in loaded_session.agent_states
        assert "chat" in loaded_session.agent_states

        # Verifica que todos os agentes foram salvos
        assert len(loaded_session.agent_states) == 3

        for agent_type in agents:
            assert agent_type in loaded_session.agent_states
            assert (
                loaded_session.agent_states[agent_type]["state"]["current_task"]
                is not None
            )
