---
name: Practical Python and Textual Examples
description: Use this skill as a practical reference for implementing core features in Python and Textual. It provides concrete code examples for dataclasses, asyncio, Pydantic validation, and key Textual methods like on_mount, set_interval, app.notify, app.push_screen, and custom widget rendering.
version: 1.0.0
author: Aura Core Team
---

# Code Examples from Web Research

## 1. Pythonic Translation

### 1.1 Python Dataclasses

Dataclasses provide a decorator (`@dataclass`) to automatically generate methods like `__init__`, `__repr__`, `__eq__`, etc., for classes primarily used to store data. They reduce boilerplate code.

**Example (`dataclass_example.py`):**

```python
from dataclasses import dataclass, field


@dataclass
class Product:
    name: str
    price: float
    quantity: int = 0
    tags: list[str] = field(default_factory=list)

    def total_cost(self) -> float:
        return self.price * self.quantity


# Example Usage
if __name__ == "__main__":
    apple = Product("Apple", 1.0, 5, ["fruit", "healthy"])
    milk = Product(name="Milk", price=2.5, quantity=2)
    bread = Product("Bread", 3.0, tags=["baked_goods"])

    print(f"Product 1: {apple}")
    print(f"Total cost of {apple.name}: ${apple.total_cost():.2f}")
    print(
        f"Are apple and another_apple equal? {apple == Product('Apple', 1.0, 5, ['fruit', 'healthy'])}"
    )
```

**Key Takeaways for Aura CLI:**
*   Dataclasses are ideal for defining simple data structures like `PromptPart` or event payloads.
*   They automatically handle initialization, representation, and comparison.
*   `field(default_factory=list)` is crucial for mutable default arguments (e.g., `tags`).

### 1.2 Python `asyncio` Event Listener

`asyncio` is Python's library for writing concurrent code using the `async`/`await` syntax. It's well-suited for event-driven programming, where tasks react to events without blocking the main thread.

**Example (`async_event_listener.py`):**

```python
import asyncio
import random
import time


async def event_producer(queue: asyncio.Queue, num_events: int):
    """
    Asynchronously produces events and puts them into the queue.
    """
    print("Producer: Starting to produce events...")
    for i in range(1, num_events + 1):
        event_data = f"Event-{i} (Value: {random.randint(1, 100)})"
        await asyncio.sleep(random.uniform(0.1, 0.5))  # Simulate work
        await queue.put(event_data)
        print(f"Producer: Produced '{event_data}'")
    await queue.put(None)  # Signal that production is complete
    print("Producer: Finished producing events.")


async def event_consumer(queue: asyncio.Queue, consumer_id: int):
    """
    Asynchronously consumes events from the queue and "listeners" to them.
    """
    print(f"Consumer {consumer_id}: Starting to listen for events...")
    while True:
        event_data = await queue.get()
        if event_data is None:
            await queue.put(None)  # Put None back for other consumers if any
            break
        print(f"Consumer {consumer_id}: Received '{event_data}'")
        await asyncio.sleep(random.uniform(0.05, 0.2))  # Simulate processing event
    print(f"Consumer {consumer_id}: Finished listening for events.")


async def main():
    """
    Main function to set up the event queue and run producer/consumer tasks.
    """
    event_queue = asyncio.Queue()
    num_events_to_produce = 10
    num_consumers = 2

    producer_task = asyncio.create_task(
        event_producer(event_queue, num_events_to_produce)
    )
    consumer_tasks = [
        asyncio.create_task(event_consumer(event_queue, i + 1))
        for i in range(num_consumers)
    ]

    await asyncio.gather(producer_task, *consumer_tasks)
    print("Main: All tasks completed.")


if __name__ == "__main__":
    asyncio.run(main())
```

**Key Takeaways for Aura CLI:**
*   `asyncio` is fundamental for event-driven, non-blocking operations in Python, crucial for a responsive TUI.
*   `asyncio.Queue` can serve as a simple event bus for inter-coroutine communication.
*   `asyncio.create_task` and `await asyncio.gather` are used to run multiple asynchronous tasks concurrently.

### 1.3 Pydantic `BaseModel` for Schema Validation

Pydantic is a data validation and settings management library using Python type hints. It allows you to define data schemas and automatically validate data when creating instances of a `BaseModel`. This is analogous to `zod` in TypeScript.

**Example:**

```python
from pydantic import BaseModel, ValidationError, Field
from typing import List, Optional


# Define a Pydantic BaseModel for a User
class User(BaseModel):
    id: int
    name: str = Field(min_length=2, max_length=50)
    email: str
    age: Optional[int] = Field(
        None, ge=0, le=120
    )  # Optional field, age between 0 and 120
    is_active: bool = True
    tags: List[str] = []


# Example 1: Valid data
print("--- Valid Data Example ---")
try:
    valid_user_data = {
        "id": 123,
        "name": "Alice Wonderland",
        "email": "alice@example.com",
        "age": 30,
        "is_active": True,
        "tags": ["admin", "developer"],
    }
    user1 = User(**valid_user_data)
    print(f"User created successfully: {user1.dict()}")
except ValidationError as e:
    print(f"Validation Error: {e}")

# Example 2: Invalid data
print("\n--- Invalid Data Example ---")
try:
    invalid_user_data = {
        "id": "not-an-int",  # Invalid type for id
        "name": "A",  # Too short for name (min_length=2)
        "email": "invalid-email",  # Not a valid email format
        "age": -5,  # Age below 0
        "is_active": "maybe",  # Invalid type for is_active
        "tags": [123, "test"],  # Invalid type in tags list
    }
    user3 = User(**invalid_user_data)
    print(f"Validation Error:\n{e.json()}")
except ValidationError as e:
    print(f"Validation Error: {e}")  # Fallback for printing if .json() fails
```

**Key Takeaways for Aura CLI:**
*   Pydantic `BaseModel` can be used to define schemas for `PromptPart`, event payloads, configuration objects, etc.
*   Automatic validation on instantiation ensures data integrity.
*   Clear error messages on validation failure aid debugging.
*   This directly aligns with the proposed `TUIEventBus` in the workplan, which suggests using `Pydantic` for event validation.

## 2. Textual Integration

### 2.1 `on_mount` Method

In Textual, the `on_mount` method is a lifecycle hook that is automatically called once when a widget is added to the DOM (Document Object Model) or the application's widget tree. It's an ideal place for initial setup, data loading, or starting animations that depend on the widget being fully rendered.

**Example:**

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.containers import Container


class MyWidget(Static):
    """A simple widget that uses on_mount."""

    def on_mount(self) -> None:
        """Called once when the widget is mounted."""
        self.update("Hello from MyWidget! This message appeared on mount.")
        self.log("MyWidget was mounted!")  # This message will appear in the Textual log


class MyApp(App):
    """A simple Textual app demonstrating on_mount."""

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container():
            yield Static("This is the main container.")
            yield MyWidget()  # MyWidget's on_mount will be called when it's added here
        yield Footer()


if __name__ == "__main__":
    app = MyApp()
    app.run()
```

**Key Takeaways for Aura CLI:**
*   `on_mount` is perfect for initial setup of widgets, such as fetching initial data, registering event listeners, or starting timers.
*   It ensures that operations are performed only when the widget is part of the active UI.

### 2.2 `set_interval` Method

The `set_interval` method in Textual allows you to schedule a function or method to be called repeatedly after a specified time interval. It's crucial for animations, polling for updates, or any task that needs to run periodically.

**Example:**

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Label
from textual.containers import Container
from textual.reactive import reactive


class IntervalApp(App[None]):
    """A simple Textual app demonstrating set_interval."""

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    counter = reactive(0)

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield Label(f"Counter: {self.counter}", id="counter_label")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Update the counter every second
        self.set_interval(1, self.update_counter)

    def update_counter(self) -> None:
        """Increments the counter and updates the label."""
        self.counter += 1
        self.query_one("#counter_label", Label).update(f"Counter: {self.counter}")

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark


if __name__ == "__main__":
    app = IntervalApp()
    app.run()
```

**Key Takeaways for Aura CLI:**
*   `self.set_interval(interval, callback)` is the primary way to schedule recurring tasks in Textual.
*   It's essential for implementing features like polling for event queue updates (as proposed in `SyncManager`), animations (like the Knight Rider spinner), or refreshing status indicators.
*   Can be used in `on_mount` to start periodic tasks when a widget becomes active.

### 2.3 `app.notify` Method

Textual's `app.notify()` method is used to display non-blocking, transient messages (toasts) to the user. It's a convenient way to provide feedback for actions, warnings, or errors without interrupting the user's flow.

**Example:**

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button
from textual.containers import Container


class NotifyApp(App[None]):
    """A simple Textual app to demonstrate notifications."""

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("n", "show_notification", "Show Notification"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield Button("Show Notification", id="notify_button", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "notify_button":
            self.action_show_notification()

    def action_show_notification(self) -> None:
        """Show a notification."""
        # Default notification
        self.notify(
            "This is a Textual notification!", title="App Notification", timeout=5
        )
        # Warning notification
        self.notify(
            "Another notification with a short timeout.", severity="warning", timeout=2
        )
        # Persistent error notification (timeout=0)
        self.notify("And a persistent error notification.", severity="error", timeout=0)


if __name__ == "__main__":
    app = NotifyApp()
    app.run()
```

**Key Takeaways for Aura CLI:**
*   `self.notify(message, title, severity, timeout)` is the standard way to display toasts in Textual.
*   `severity` (e.g., "warning", "error", "information") changes the notification's appearance.
*   `timeout=0` makes a notification persistent until manually dismissed.
*   This directly relates to the proposed `ToastProvider` in the workplan, which would likely wrap this `notify` functionality or provide a more customized toast rendering.

### 2.4 `app.push_screen` Method

In Textual, `app.push_screen()` is used to display a new screen on top of the current one, creating a navigation stack. This is fundamental for building multi-screen applications. `app.pop_screen()` removes the top screen, returning to the previous one.

**Example:**

```python
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Label


class HomeScreen(Screen):
    """The first screen in our app."""

    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Welcome to the Home Screen!"),
            Button("Go to Detail Screen", id="go_to_detail", variant="primary"),
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "go_to_detail":
            self.app.push_screen(DetailScreen())  # Push the detail screen


class DetailScreen(Screen):
    """A screen pushed on top of the home screen."""

    BINDINGS = [("b", "pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("You are now on the Detail Screen."),
            Button("Go Back", id="go_back", variant="warning"),
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "go_back":
            self.app.pop_screen()  # Pop back to the previous screen


class MyTextualApp(App):
    """A simple Textual app demonstrating screen pushing and popping."""

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]
    # Define our screens, so they can be referred to by string name later if needed,
    # though for push_screen we can also pass an instance directly.
    SCREENS = {
        "home": HomeScreen,
        "detail": DetailScreen,
    }

    def on_mount(self) -> None:
        """Called after the app is mounted."""
        self.push_screen("home")  # Push the initial screen


if __name__ == "__main__":
    app = MyTextualApp()
    app.run()
```

**Key Takeaways for Aura CLI:**
*   `push_screen(screen_instance_or_name)` adds a new screen to the stack, making it active.
*   `pop_screen()` removes the current screen, returning to the previous one.
*   This mechanism is directly relevant to the proposed `Router` system in the workplan (GAP-010), which would abstract and manage this screen stack for declarative navigation.

## 3. Handling Complexity

### 3.1 Custom Widget Rendering

Textual allows developers to create custom widgets by inheriting from `textual.widget.Widget` and overriding the `render()` method. This method should return a string (potentially using Textual's rich text markup) that represents the visual output of the widget. This is essential for creating unique UI elements not provided by Textual's built-in widgets.

**Example:**

```python
from textual.app import App, ComposeResult
from textual.widget import Widget
from textual.reactive import var
from textual.widgets import Header, Footer, Button, Static
from textual.containers import Container
from textual.color import Color  # Import Color for custom colors


class CustomBox(Widget):
    """A simple custom widget that renders a colored box with text."""

    text = var("Hello Custom Widget!")
    box_color = var(Color(0, 100, 200))  # Default to a shade of blue

    def __init__(
        self,
        text: str = "Hello Custom Widget!",
        box_color: Color = Color(0, 100, 200),
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.text = text
        self.box_color = box_color

    def render(self) -> str:
        """
        Renders the widget. This method should return a string representing
        the content to be displayed.
        """
        width = self.size.width
        height = self.size.height

        if width == 0 or height == 0:
            return ""

        display_text = self.text
        if len(display_text) > width - 2:
            display_text = display_text[: width - 5] + "..."

        padding_left = (width - len(display_text)) // 2
        centered_text = (
            " " * padding_left
            + display_text
            + " " * (width - len(display_text) - padding_left)
        )

        lines = []
        for i in range(height):
            if i == height // 2:  # Center line for text
                # Use Textual's rich text markup for background color
                line = f"[on {self.box_color.hex}]{centered_text}[/ ]"
            else:
                line = f"[on {self.box_color.hex}]{' ' * width}[/ ]"
            lines.append(line)

        return "\n".join(lines)


class CustomWidgetApp(App):
    """A Textual app to demonstrate the custom widget."""

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("c", "change_color", "Change Box Color"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container():
            yield Static(
                "Observe the custom rendered widget below:", classes="instructions"
            )
            yield CustomBox(
                id="my_custom_box", text="Textual rocks!", box_color=Color(200, 50, 0)
            )
            yield Static(
                "Another custom box with different properties:", classes="instructions"
            )
            yield CustomBox(
                id="another_custom_box",
                text="Dynamic content!",
                box_color=Color(50, 150, 50),
            )
        yield Footer()

    def action_change_color(self) -> None:
        """An action to change the color of the first custom box."""
        custom_box = self.query_one("#my_custom_box", CustomBox)
        current_color = custom_box.box_color
        if current_color == Color(200, 50, 0):
            custom_box.box_color = Color(0, 100, 200)
            custom_box.text = "Now blue!"
        elif current_color == Color(0, 100, 200):
            custom_box.box_color = Color(200, 180, 0)
            custom_box.text = "Now yellow!"
        else:
            custom_box.box_color = Color(200, 50, 0)
            custom_box.text = "Back to red!"


if __name__ == "__main__":
    app = CustomWidgetApp()
    app.run()
```

**Key Takeaways for Aura CLI:**
*   Overriding `render()` is the pathway to creating highly customized visual components in Textual.
*   Reactive variables (`textual.reactive.var`) automatically trigger re-renders when their values change, making custom widgets dynamic.
*   Textual's rich text markup can be used within `render()` to apply styles like colors and backgrounds.
*   This approach is crucial for implementing the `RichPromptInput` (GAP-002) to display "extmarks" and rich parts within the input area.
