from __future__ import annotations

from queue import Queue

from aura_cli.tui.bridge import TextualUIManager
from aura_cli.tui.keybinds.keybind_manager import LeaderKeyManager
from aura_cli.tui.plugin_manager import PluginManager


class FakeTimer:
    def __init__(self) -> None:
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class FakeApp:
    def __init__(self) -> None:
        self.timers: list[FakeTimer] = []
        self.notifications: list[str] = []
        self.events: list[str] = []
        self.focused = None
        self.is_running = True

    def set_interval(self, _interval: float, _callback) -> FakeTimer:
        timer = FakeTimer()
        self.timers.append(timer)
        return timer

    def set_timer(self, _timeout: float, _callback) -> FakeTimer:
        return self.set_interval(_timeout, _callback)

    def notify(self, message: str, **_kwargs) -> None:
        self.notifications.append(message)


def test_plugin_manager_injects_app_and_unloads_all_plugins(tmp_path) -> None:
    plugin_file = tmp_path / "fake_wave6_plugin.py"
    plugin_file.write_text(
        """
from aura_cli.tui.plugin_manager import AuraTUIPluginBase


class FakePlugin(AuraTUIPluginBase):
    PLUGIN_NAME = 'fake-wave6'

    def get_widgets(self):
        return {}

    def on_load(self):
        self.app.events.append('load')

    def on_unload(self):
        self.app.events.append('unload')

    def on_app_ready(self):
        self.app.events.append('ready')
""",
        encoding="utf-8",
    )
    app = FakeApp()
    manager = PluginManager(plugin_dirs=[str(tmp_path)], app=app)

    manager.load_plugins()
    manager.notify_app_ready()
    manager.unload_plugins()
    manager.unload_plugins()

    assert app.events == ["load", "ready", "unload"]
    assert manager.loaded_plugins == {}
    assert manager.available_widgets == {}
    assert manager.plugin_commands == {}
    assert manager.plugin_keybindings == []


def test_fallback_timers_are_stopped_and_stop_is_idempotent() -> None:
    app = FakeApp()
    bridge = TextualUIManager(app, status_queue=Queue(), stats=object())

    bridge._init_fallback_polling()
    assert len(bridge._fallback_timers) == 3

    bridge.stop()
    bridge.stop()

    assert bridge._fallback_timers == []
    assert all(timer.stopped for timer in app.timers)
    assert bridge._heartbeat_timer_started is False


def test_leader_manager_stop_cancels_timer_and_state() -> None:
    app = FakeApp()
    leader = LeaderKeyManager(app)

    leader.enter_leader_mode()
    timer = app.timers[-1]
    leader.stop()
    leader.stop()

    assert timer.stopped is True
    assert leader.state.active is False
    assert leader.state.sequence == []
    assert leader._timer is None
