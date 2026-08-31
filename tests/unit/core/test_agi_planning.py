"""Testes para core/agi/planning.py — TEST-NEW-01."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from aura_cli.core.agi.planning import AgiPlanner


def _make_planner(**kwargs):
    adapter = MagicMock()
    adapter.emit_chat_message = MagicMock()
    human_adapter = MagicMock()
    defaults = {
        "model": "gemini-2.5-flash",
        "project_root": Path("/tmp"),
        "agi_event_adapter": adapter,
        "human_intervention_adapter": human_adapter,
    }
    defaults.update(kwargs)
    return AgiPlanner(**defaults)


class TestAgiPlannerInit:
    def test_default_allowed_task_types(self):
        p = _make_planner()
        assert "read_file" in p.allowed_task_types
        assert "write_file" in p.allowed_task_types
        assert "run_tests" in p.allowed_task_types

    def test_custom_allowed_task_types(self):
        p = _make_planner(allowed_task_types=["read_file"])
        assert p.allowed_task_types == ["read_file"]

    def test_model_stored(self):
        p = _make_planner(model="gpt-4o")
        assert p.model == "gpt-4o"


class TestCallPlanningLlm:
    def test_returns_none_on_empty_response(self):
        p = _make_planner()
        with patch("aura_cli.core.agi.planning.query_with_fallback", return_value=None):
            result = p._call_planning_llm([])
        assert result is None

    def test_strips_json_fences(self):
        p = _make_planner()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = '```json\n{"tasks": []}\n```'
        with patch(
            "aura_cli.core.agi.planning.query_with_fallback", return_value=mock_resp
        ):
            result = p._call_planning_llm([])
        assert result == '{"tasks": []}'

    def test_strips_plain_fences(self):
        p = _make_planner()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = '```\n{"tasks": []}\n```'
        with patch(
            "aura_cli.core.agi.planning.query_with_fallback", return_value=mock_resp
        ):
            result = p._call_planning_llm([])
        assert result == '{"tasks": []}'

    def test_returns_content_as_string(self):
        p = _make_planner()
        mock_resp = MagicMock()
        mock_resp.choices[
            0
        ].message.content = '{"tasks": [{"id": "t1", "type": "read_file"}]}'
        with patch(
            "aura_cli.core.agi.planning.query_with_fallback", return_value=mock_resp
        ):
            result = p._call_planning_llm([])
        assert isinstance(result, str)
        assert "tasks" in result


class TestParsePlanResponse:
    def test_valid_plan(self):
        p = _make_planner()
        plan_json = json.dumps(
            {
                "tasks": [
                    {
                        "id": "t1",
                        "type": "read_file",
                        "description": "Ler arquivo",
                        "parameters": {"path": "README.md"},
                    }
                ]
            }
        )
        result = p._parse_plan_response(plan_json)
        assert result is not None
        assert len(result) == 1
        assert result[0]["id"] == "t1"

    def test_invalid_task_type_skipped(self):
        p = _make_planner()
        plan_json = json.dumps(
            {
                "tasks": [
                    {
                        "id": "t1",
                        "type": "invalid_type",
                        "description": "X",
                        "parameters": {},
                    }
                ]
            }
        )
        result = p._parse_plan_response(plan_json)
        assert result is None  # all tasks skipped → None

    def test_empty_tasks_returns_none(self):
        p = _make_planner()
        result = p._parse_plan_response('{"tasks": []}')
        assert result is None

    def test_invalid_json_returns_none(self):
        p = _make_planner()
        result = p._parse_plan_response("not json at all")
        assert result is None

    def test_multiple_tasks(self):
        p = _make_planner()
        plan_json = json.dumps(
            {
                "tasks": [
                    {
                        "id": "t1",
                        "type": "read_file",
                        "description": "A",
                        "parameters": {"path": "a.py"},
                    },
                    {
                        "id": "t2",
                        "type": "list_directory",
                        "description": "B",
                        "parameters": {"path": "."},
                    },
                ]
            }
        )
        result = p._parse_plan_response(plan_json)
        assert result is not None
        assert len(result) == 2

    def test_task_without_id_gets_generated_id(self):
        p = _make_planner()
        plan_json = json.dumps(
            {
                "tasks": [
                    {
                        "type": "read_file",
                        "description": "X",
                        "parameters": {"path": "x.py"},
                    }
                ]
            }
        )
        result = p._parse_plan_response(plan_json)
        assert result is not None
        assert result[0]["id"]  # should have auto-generated id

    def test_emits_success_event(self):
        p = _make_planner()
        plan_json = json.dumps(
            {
                "tasks": [
                    {
                        "id": "t1",
                        "type": "read_file",
                        "description": "A",
                        "parameters": {"path": "a.py"},
                    }
                ]
            }
        )
        p._parse_plan_response(plan_json)
        p.agi_event_adapter.emit_chat_message.assert_called_once()
