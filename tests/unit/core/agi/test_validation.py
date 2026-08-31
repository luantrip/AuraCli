"""Tests for core/agi/validation.py — AgiValidator."""

from unittest.mock import MagicMock, patch

with patch("aura_cli.core.memory.constitution_validator.ConstitutionValidator"):
    with patch(
        "aura_cli.core.ui_bridge.UIIcons",
        MagicMock(
            WARNING="⚠", ERROR="❌", INFO="ℹ", SUCCESS="✓", THINKING="🤔", WORKING="⚙"
        ),
    ):
        from aura_cli.core.agi.validation import AgiValidator


def _make_validator(constitution=None, **kwargs):
    defaults = {
        "constitution": constitution,
        "agi_event_adapter": MagicMock(),
        "linter_manager": None,
        "memory_service": None,
        "session_state": None,
        "tester_worker_class": None,
        "headless": False,
    }
    defaults.update(kwargs)
    with patch("aura_cli.core.agi.validation.ConstitutionValidator") as MockCV:
        MockCV.return_value = MagicMock()
        v = AgiValidator(**defaults)
    return v


class TestInit:
    def test_no_constitution(self):
        v = _make_validator(constitution=None)
        assert v.constitution is None
        assert v.constitution_validator is None
        assert v.learned_rules == []

    def test_with_constitution(self):
        v = _make_validator(constitution="rules here")
        assert v.constitution == "rules here"
        assert v.constitution_validator is not None


class TestValidateAndSanitizePrompt:
    def test_no_constitution_returns_prompt_unchanged(self):
        v = _make_validator(constitution=None)
        assert v.validate_and_sanitize_prompt("hello") == "hello"

    def test_valid_prompt_prepends_context(self):
        v = _make_validator(constitution="rules")
        v.constitution_validator.validate_prompt.return_value = (True, [], None)
        result = v.validate_and_sanitize_prompt("build api")
        assert "build api" in result
        assert "Constituição" in result

    def test_violations_emits_messages(self):
        v = _make_validator(constitution="rules")
        v.constitution_validator.validate_prompt.return_value = (
            False,
            ["violation 1"],
            "sanitized prompt",
        )
        v.constitution_validator.check_conflict.return_value = None
        result = v.validate_and_sanitize_prompt("bad prompt")
        assert result == "sanitized prompt"
        v.agi_event_adapter.emit_chat_message.assert_called()

    def test_critical_conflict_logged(self):
        v = _make_validator(constitution="rules")
        v.constitution_validator.validate_prompt.return_value = (
            False,
            ["v1"],
            "sanitized",
        )
        v.constitution_validator.check_conflict.return_value = "CRITICAL"
        v.validate_and_sanitize_prompt("bad")
        # Should have called emit at least 3 times (violation header, detail, critical)
        assert v.agi_event_adapter.emit_chat_message.call_count >= 3


class TestExtractLearnedRules:
    def test_empty_response(self):
        v = _make_validator(constitution="x")
        v.extract_learned_rules_from_response("")
        assert v.learned_rules == []

    def test_no_constitution(self):
        v = _make_validator(constitution=None)
        v.extract_learned_rules_from_response("vamos usar pytest para testes")
        assert v.learned_rules == []

    def test_extracts_decision(self):
        v = _make_validator(constitution="x")
        v.extract_learned_rules_from_response(
            "decidimos usar pytest como framework de testes principal."
        )
        assert len(v.learned_rules) >= 1
        assert v.learned_rules[0]["category"] == "decisão"

    def test_extracts_pattern(self):
        v = _make_validator(constitution="x")
        v.extract_learned_rules_from_response(
            "padrão Repository para acesso ao banco de dados."
        )
        assert any(r["category"] == "padrão" for r in v.learned_rules)

    def test_extracts_prohibition(self):
        v = _make_validator(constitution="x")
        v.extract_learned_rules_from_response(
            "evitar usar variáveis globais no código."
        )
        assert any(r["category"] == "proibição" for r in v.learned_rules)

    def test_ignores_short_matches(self):
        v = _make_validator(constitution="x")
        v.extract_learned_rules_from_response("decidimos x.")
        assert v.learned_rules == []


class TestConsolidateLearnedRules:
    def test_no_rules_does_nothing(self):
        v = _make_validator(constitution="x", memory_service=MagicMock())
        v.learned_rules = []
        v.consolidate_learned_rules(MagicMock())
        v.memory_service.add_learned_rule.assert_not_called()

    def test_no_memory_service_does_nothing(self):
        v = _make_validator(constitution="x", memory_service=None)
        v.learned_rules = [{"content": "rule", "category": "test"}]
        v.consolidate_learned_rules(MagicMock())
        # No crash

    def test_no_constitution_does_nothing(self):
        v = _make_validator(constitution=None, memory_service=MagicMock())
        v.learned_rules = [{"content": "rule", "category": "test"}]
        v.consolidate_learned_rules(MagicMock())
        v.memory_service.add_learned_rule.assert_not_called()

    def test_saves_rules_and_clears(self):
        mem = MagicMock()
        v = _make_validator(constitution="x", memory_service=mem)
        v.learned_rules = [
            {"content": "use pytest", "category": "decisão"},
            {"content": "snake_case naming", "category": "padrão"},
        ]
        config = MagicMock()
        config.get.return_value = False  # no auto_consolidation
        v.consolidate_learned_rules(config)
        assert mem.add_learned_rule.call_count == 2
        assert v.learned_rules == []

    def test_auto_consolidation_updates_constitution(self):
        mem = MagicMock()
        mem.consolidate_rules.return_value = True
        mem.get_constitution.return_value = "new constitution"
        session = MagicMock()
        v = _make_validator(
            constitution="old", memory_service=mem, session_state=session
        )
        v.learned_rules = [{"content": "rule text here", "category": "test"}]
        config = MagicMock()
        config.get.return_value = True  # auto_consolidation enabled
        v.consolidate_learned_rules(config)
        assert v.constitution == "new constitution"
        session.update_constitution.assert_called_once_with("new constitution")

    def test_exception_handled_gracefully(self):
        mem = MagicMock()
        mem.add_learned_rule.side_effect = RuntimeError("db error")
        v = _make_validator(constitution="x", memory_service=mem)
        v.learned_rules = [{"content": "rule content here", "category": "t"}]
        v.consolidate_learned_rules(MagicMock())
        # Should not raise


class TestAutoValidateGeneratedFiles:
    def test_empty_files_does_nothing(self):
        v = _make_validator(linter_manager=MagicMock())
        v.auto_validate_generated_files([])
        v.linter_manager.validate_generated_files.assert_not_called()

    def test_no_linter_manager(self):
        v = _make_validator(linter_manager=None)
        v.auto_validate_generated_files(["file.py"])
        # No crash

    def test_all_valid(self, tmp_path):
        f = tmp_path / "good.py"
        f.write_text("x = 1")
        linter = MagicMock()
        linter.validate_generated_files.return_value = {str(f): (True, "")}
        v = _make_validator(linter_manager=linter)
        v.auto_validate_generated_files([str(f)])
        v.agi_event_adapter.emit_chat_message.assert_called()

    def test_errors_found(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("x =")
        linter = MagicMock()
        linter.validate_generated_files.return_value = {str(f): (False, "syntax error")}
        v = _make_validator(linter_manager=linter)
        v.auto_validate_generated_files([str(f)])
        # Should emit warning message
        calls = v.agi_event_adapter.emit_chat_message.call_args_list
        assert any("erro" in str(c).lower() for c in calls)

    def test_nonexistent_files_skipped(self):
        linter = MagicMock()
        linter.validate_generated_files.return_value = {}
        v = _make_validator(linter_manager=linter)
        v.auto_validate_generated_files(["/nonexistent/file.py"])
        # Should not crash; file is filtered before linter call


class TestRunAdversarialValidation:
    def test_no_tester_worker_returns_none(self):
        v = _make_validator(tester_worker_class=None)
        result = v.run_adversarial_validation(["f.py"], "model", {}, {}, MagicMock())
        assert result is None

    def test_empty_files_returns_none(self):
        v = _make_validator(tester_worker_class=MagicMock())
        result = v.run_adversarial_validation([], "model", {}, {}, MagicMock())
        assert result is None

    def test_nonexistent_file_skipped(self):
        v = _make_validator(tester_worker_class=MagicMock())
        result = v.run_adversarial_validation(
            ["/nonexistent.py"], "model", {}, {}, MagicMock()
        )
        assert result is None

    def test_successful_validation(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("def hello(): pass")
        tester_cls = MagicMock()
        mock_tester = MagicMock()
        mock_tester.is_alive.return_value = False
        mock_tester.get_result.return_value = {
            "status": "completed",
            "issues_found": [{"severity": "low", "msg": "unused var"}],
            "tests_generated": ["test_1"],
            "analysis": "looks ok",
        }
        tester_cls.return_value = mock_tester
        v = _make_validator(tester_worker_class=tester_cls)
        result = v.run_adversarial_validation([str(f)], "model", {}, {}, MagicMock())
        assert result is not None
        assert result["status"] == "completed"
        assert result["files_validated"] == 1
        assert result["total_issues"] == 1

    def test_tester_exception_handled(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("x = 1")
        tester_cls = MagicMock(side_effect=RuntimeError("tester crash"))
        v = _make_validator(tester_worker_class=tester_cls)
        result = v.run_adversarial_validation([str(f)], "model", {}, {}, MagicMock())
        # Should not crash, returns None since no successful results
        assert result is None
