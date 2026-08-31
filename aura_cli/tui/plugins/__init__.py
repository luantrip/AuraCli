"""
Aura TUI Plugins Directory.

Place your custom TUI plugins here.
Each plugin should be a .py file that defines classes inheriting from AuraTUIPluginWidget.

Plugin example:
```python
from aura_cli.tui.plugin_manager import AuraTUIPluginWidget
from textual.widgets import Static

class MyCustomWidget(Static):
    def compose(self):
        yield Static("Hello from my plugin!")

class MyPlugin(AuraTUIPluginWidget):
    WIDGET_CLASS = MyCustomWidget
    WIDGET_NAME = "My Custom Widget"
    WIDGET_LOCATION = "dashboard"
```
"""
