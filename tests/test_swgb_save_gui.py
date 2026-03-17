from __future__ import absolute_import, division

import importlib
import runpy
import sys
import types
from pathlib import Path
from typing import Dict, List, Tuple

import pytest


class FakeStringVar:
    def __init__(self, value: str = ""):
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class FakeWidget:
    def __init__(self, *_args, **kwargs):
        self.state = kwargs.get("state")
        self.textvariable = kwargs.get("textvariable")
        self.command = kwargs.get("command")
        self.destroyed = False
        self._layout_calls: Dict[str, Tuple[Tuple[object, ...], Dict[str, object]]] = {}

    def grid(self, *args, **kwargs):
        self._layout_calls["grid"] = (args, kwargs)

    def pack(self, *args, **kwargs):
        self._layout_calls["pack"] = (args, kwargs)

    def configure(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    config = configure

    def columnconfigure(self, *args, **kwargs):
        self._layout_calls["columnconfigure"] = (args, kwargs)

    def rowconfigure(self, *args, **kwargs):
        self._layout_calls["rowconfigure"] = (args, kwargs)

    def destroy(self):
        self.destroyed = True

    @staticmethod
    def set(*_args, **_kwargs):
        # Test double: Tk scrollbars call into this, but the fake widget ignores it.
        pass


class FakeRoot(FakeWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._window_state: Dict[str, object] = {}
        self.mainloop_called = False

    def title(self, value: str) -> None:
        self._window_state["title"] = value

    def geometry(self, value: str) -> None:
        self._window_state["geometry"] = value

    def transient(self, _parent) -> None:
        self._window_state["transient_parent"] = _parent

    def grab_set(self) -> None:
        self._window_state["grabbed"] = True

    def update(self) -> None:
        self._window_state["updated"] = True

    def wait_window(self, _window) -> None:
        self._window_state["waited"] = True

    def resizable(self, width: bool, height: bool) -> None:
        self._window_state["resizable_args"] = (width, height)

    def mainloop(self) -> None:
        self.mainloop_called = True

    @staticmethod
    def winfo_rootx() -> int:
        return 50

    @staticmethod
    def winfo_rooty() -> int:
        return 60

    @staticmethod
    def winfo_width() -> int:
        return 400

    @staticmethod
    def winfo_height() -> int:
        return 300


class FakeTreeview(FakeWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rows = {}
        self.order = []
        self.selected = ()

    @staticmethod
    def heading(*_args, **_kwargs):
        # Test double: column headings are irrelevant to the GUI behavior under test.
        pass

    @staticmethod
    def column(*_args, **_kwargs):
        # Test double: width configuration is intentionally ignored in tests.
        pass

    @staticmethod
    def yview(*_args, **_kwargs):
        # Test double: vertical scrolling state is not modeled in these tests.
        pass

    def insert(self, _parent, _index, values):
        item_id = f"item-{len(self.order)}"
        self.rows[item_id] = list(values)
        self.order.append(item_id)
        return item_id

    def get_children(self):
        return tuple(self.order)

    def delete(self, item_id):
        self.rows.pop(item_id, None)
        self.order = [item for item in self.order if item != item_id]

    def item(self, item_id, values=None):
        if values is not None:
            self.rows[item_id] = list(values)
        return {"values": self.rows[item_id]}

    def index(self, item_id):
        return self.order.index(item_id)

    def selection(self):
        return self.selected

    def selection_set(self, item_id):
        self.selected = (item_id,)


def test_fake_widget_helpers_are_noops() -> None:
    widget = FakeWidget()
    tree = FakeTreeview()

    assert widget.set("a", "b") is None  # nosec B101
    assert tree.yview("moveto", 0) is None  # nosec B101


def install_fake_tk(monkeypatch: pytest.MonkeyPatch):
    message_calls: Dict[str, List[Tuple[str, str]]] = {"error": [], "warning": [], "info": []}
    dialog_state = {"filename": ""}

    ttk_module = types.ModuleType("tkinter.ttk")
    for widget_name, widget_value in {
        "Label": FakeWidget,
        "Entry": FakeWidget,
        "Frame": FakeWidget,
        "Button": FakeWidget,
        "Treeview": FakeTreeview,
        "Scrollbar": FakeWidget,
    }.items():
        setattr(ttk_module, widget_name, widget_value)

    filedialog_module = types.ModuleType("tkinter.filedialog")
    setattr(filedialog_module, "askopenfilename", lambda **_kwargs: dialog_state["filename"])

    messagebox_module = types.ModuleType("tkinter.messagebox")
    setattr(messagebox_module, "showerror", lambda *args: message_calls["error"].append(args))
    setattr(messagebox_module, "showwarning", lambda *args: message_calls["warning"].append(args))
    setattr(messagebox_module, "showinfo", lambda *args: message_calls["info"].append(args))

    tk_module = types.ModuleType("tkinter")
    tk_members: Dict[str, object] = {
        "Tk": FakeRoot,
        "Toplevel": FakeRoot,
        "StringVar": FakeStringVar,
        "W": "W",
        "E": "E",
        "N": "N",
        "S": "S",
        "LEFT": "LEFT",
        "VERTICAL": "VERTICAL",
        "DISABLED": "disabled",
        "NORMAL": "normal",
        "SUNKEN": "sunken",
        "ttk": ttk_module,
        "filedialog": filedialog_module,
        "messagebox": messagebox_module,
    }
    for member_name, member_value in tk_members.items():
        setattr(tk_module, member_name, member_value)

    monkeypatch.setitem(sys.modules, "tkinter", tk_module)
    monkeypatch.setitem(sys.modules, "tkinter.ttk", ttk_module)
    monkeypatch.setitem(sys.modules, "tkinter.filedialog", filedialog_module)
    monkeypatch.setitem(sys.modules, "tkinter.messagebox", messagebox_module)

    module = importlib.import_module("swgb_save_gui")
    module = importlib.reload(module)
    return module, dialog_state, message_calls


def test_edit_resource_dialog_accepts_valid_values(monkeypatch: pytest.MonkeyPatch) -> None:
    gui, _dialog_state, message_calls = install_fake_tk(monkeypatch)

    dialog = gui.EditResourceDialog(gui.tk.Tk(), "Player One", [1.0, 2.0, 3.0, 4.0])
    dialog.entries["Carbon"].set("10")
    dialog.entries["Food"].set("20")
    dialog.entries["Nova"].set("30")
    dialog.entries["Ore"].set("40")

    dialog.ok()

    assert dialog.result == [10.0, 20.0, 30.0, 40.0]  # nosec B101
    assert dialog.dialog.destroyed is True  # nosec B101
    assert not message_calls["error"]  # nosec B101


def test_edit_resource_dialog_rejects_invalid_values(monkeypatch: pytest.MonkeyPatch) -> None:
    gui, _dialog_state, message_calls = install_fake_tk(monkeypatch)

    dialog = gui.EditResourceDialog(gui.tk.Tk(), "Player One", [1.0, 2.0, 3.0, 4.0])
    dialog.entries["Carbon"].set("-1")

    dialog.ok()

    assert dialog.result is None  # nosec B101
    assert dialog.dialog.destroyed is False  # nosec B101
    assert message_calls["error"]  # nosec B101


def test_edit_resource_dialog_handles_unexpected_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    gui, _dialog_state, message_calls = install_fake_tk(monkeypatch)

    dialog = gui.EditResourceDialog(gui.tk.Tk(), "Player One", [1.0, 2.0, 3.0, 4.0])

    class BrokenVar:  # pylint: disable=too-few-public-methods
        @staticmethod
        def get():
            raise RuntimeError("boom")

    dialog.entries["Carbon"] = BrokenVar()

    dialog.ok()

    assert dialog.result is None  # nosec B101
    assert dialog.dialog.destroyed is False  # nosec B101
    assert message_calls["error"][-1] == ("Error", "Failed to save changes: boom")  # nosec B101


def test_edit_resource_dialog_cancel_closes_dialog(monkeypatch: pytest.MonkeyPatch) -> None:
    gui, _dialog_state, _message_calls = install_fake_tk(monkeypatch)

    dialog = gui.EditResourceDialog(gui.tk.Tk(), "Player One", [1.0, 2.0, 3.0, 4.0])
    dialog.cancel()

    assert dialog.dialog.destroyed is True  # nosec B101


def test_save_game_gui_loads_browse_edit_and_save_flows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    gui, dialog_state, message_calls = install_fake_tk(monkeypatch)

    class FakePlayer:  # pylint: disable=too-few-public-methods
        def __init__(self, name, index, resources):
            self.name = name
            self.index = index
            self.resources = resources

    class FakeSaveGame:
        def __init__(self, filename: str):
            self.filename = filename
            self.players = [FakePlayer("Alpha", 1, [10.0, 20.0, 30.0, 40.0])]
            self.saved = False

        @staticmethod
        def read():
            # Test double: loading is exercised by the GUI flow, not the fake save backend.
            pass

        def save(self, _filename):
            self.saved = True

    monkeypatch.setattr(gui, "SaveGame", FakeSaveGame)
    root = gui.tk.Tk()
    app = gui.SaveGameGUI(root)

    dialog_state["filename"] = str(tmp_path / "save.ga2")
    Path(dialog_state["filename"]).write_bytes(b"save-bytes")
    app.browse_file()
    assert app.file_path.get() == dialog_state["filename"]  # nosec B101

    app.tree.insert("", "end", values=["stale"])
    app.load_save()
    tree_items = app.tree.get_children()
    assert len(tree_items) == 1  # nosec B101
    assert app.tree.item(tree_items[0])["values"][0] != "stale"  # nosec B101
    assert app.scrollbar.set("ignored") is None  # nosec B101
    assert app.tree.yview() is None  # nosec B101
    assert app.edit_button.state == gui.tk.NORMAL  # nosec B101
    assert app.save_button.state == gui.tk.NORMAL  # nosec B101
    assert "Loaded 1 players" in app.status_var.get()  # nosec B101

    app.tree.selection_set(tree_items[0])

    class FakeDialog:  # pylint: disable=too-few-public-methods
        def __init__(self, *_args, **_kwargs):
            self.dialog = object()
            self.result = [100.0, 200.0, 300.0, 400.0]

    monkeypatch.setattr(gui, "EditResourceDialog", FakeDialog)
    app.edit_resources()
    assert app.current_save.players[0].resources == [100.0, 200.0, 300.0, 400.0]  # nosec B101
    assert "Updated resources" in app.status_var.get()  # nosec B101

    app.save_changes()
    assert message_calls["info"]  # nosec B101
    assert "Changes saved successfully" in app.status_var.get()  # nosec B101


def test_save_game_gui_handles_missing_selection_and_save_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    gui, _dialog_state, message_calls = install_fake_tk(monkeypatch)
    root = gui.tk.Tk()
    app = gui.SaveGameGUI(root)

    app.edit_resources()
    assert message_calls["warning"]  # nosec B101

    class FailingSave:  # pylint: disable=too-few-public-methods
        @staticmethod
        def save(_filename):
            raise RuntimeError("boom")

    app.current_save = FailingSave()
    app.file_path.set(str(tmp_path / "save.ga2"))
    Path(app.file_path.get()).write_bytes(b"save")

    app.save_changes()
    assert message_calls["error"]  # nosec B101
    assert app.status_var.get() == "Error saving changes"  # nosec B101


def test_load_save_requires_a_path(monkeypatch: pytest.MonkeyPatch) -> None:
    gui, _dialog_state, message_calls = install_fake_tk(monkeypatch)
    app = gui.SaveGameGUI(gui.tk.Tk())

    app.load_save()

    assert message_calls["error"]  # nosec B101


def test_load_save_surfaces_read_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    gui, dialog_state, message_calls = install_fake_tk(monkeypatch)

    class BrokenSaveGame:  # pylint: disable=too-few-public-methods
        def __init__(self, _filename: str):
            self.players: List[object] = []

        def read(self) -> None:
            _ = self.players
            raise RuntimeError("parse boom")

    monkeypatch.setattr(gui, "SaveGame", BrokenSaveGame)
    app = gui.SaveGameGUI(gui.tk.Tk())
    dialog_state["filename"] = str(tmp_path / "broken.ga2")
    Path(dialog_state["filename"]).write_bytes(b"save")
    app.file_path.set(dialog_state["filename"])

    app.load_save()

    assert message_calls["error"][-1] == ("Error", "Failed to load save file: parse boom")  # nosec B101
    assert app.status_var.get() == "Error loading file"  # nosec B101


def test_save_changes_returns_early_when_no_current_save(monkeypatch: pytest.MonkeyPatch) -> None:
    gui, _dialog_state, message_calls = install_fake_tk(monkeypatch)
    app = gui.SaveGameGUI(gui.tk.Tk())

    app.save_changes()

    assert message_calls == {"error": [], "warning": [], "info": []}  # nosec B101


def test_main_builds_gui_and_enters_mainloop(monkeypatch: pytest.MonkeyPatch) -> None:
    gui, _dialog_state, _message_calls = install_fake_tk(monkeypatch)
    root = gui.tk.Tk()
    monkeypatch.setattr(gui.tk, "Tk", lambda: root)
    captured = {}

    class FakeApp:  # pylint: disable=too-few-public-methods
        def __init__(self, passed_root):
            captured["root"] = passed_root

    monkeypatch.setattr(gui, "SaveGameGUI", FakeApp)

    gui.main()

    assert captured["root"] is root  # nosec B101
    assert root.mainloop_called is True  # nosec B101


def test_running_swgb_save_gui_as_main_executes_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    gui, _dialog_state, _message_calls = install_fake_tk(monkeypatch)
    root = gui.tk.Tk()
    monkeypatch.setattr(gui.tk, "Tk", lambda: root)

    runpy.run_path(str(Path(gui.__file__)), run_name="__main__")

    assert root.mainloop_called is True  # nosec B101
