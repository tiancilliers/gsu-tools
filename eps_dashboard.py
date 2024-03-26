from textual.app import App, ComposeResult
from textual.widgets import Label, Button, Header

class MyApp(App):
    CSS_PATH = "style.tcss"	
    TITLE = "EPS Dashboard"
    SUB_TITLE = "ESL GSU Tools"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Hello, World!", id="question")
        yield Button("Press me", id="b1", variant="primary")
        yield Button("Press me", id="b2", variant="error")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.query_one(Label).label = f"Button {event.button.id} pressed"

if __name__ == "__main__":
    app = MyApp()
    app.run()