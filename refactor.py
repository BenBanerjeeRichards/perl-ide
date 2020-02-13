from .server import *
from .util import *
import sublime
import sublime_plugin
import threading


def rename_symbol(path, project_files, rename_to, line, col):
    res = post_request("rename", {
        "line": line,
        "col": col,
        "path": path,
        "projectFiles": project_files,
        "renameTo": rename_to
    })

    if not res["success"]:
        log_error("Find usages failed with error - {}:{}".format(res.get("error"), res.get("errorMessage")))
        return res.get("errorMessage")

    if "body" not in res:
        log_error("Bad JSON for find_usages: no body")
        return None

    return res["body"]


def is_symbol(path, project_files, line, col):
    res = post_request("is-symbol", {
        "line": line,
        "col": col,
        "path": path,
        "projectFiles": project_files
    })

    if not res["success"]:
        log_error("Find usages failed with error - {}:{}".format(res.get("error"), res.get("errorMessage")))
        return None

    if "body" not in res:
        log_error("Bad JSON for find_usages: no body")
        return None

    return res["body"]


class RenameThread(threading.Thread):

    def __init__(self, on_complete, path, project_files, rename_to, line, col):
        super(RenameThread, self).__init__()
        self.on_complete = on_complete
        self.path = path
        self.project_files = project_files
        self.line = line
        self.rename_to = rename_to
        self.col = col

    def run(self):
        return self.on_complete(rename_symbol(self.path, self.project_files, self.rename_to, self.line, self.col))


def rename_complete(res):
    if res is not None:
        sublime.active_window().active_view().show_popup("Error - {}".format(res))


class RenameSymbolCommand(sublime_plugin.WindowCommand):

    def run(self, event=None):
        self.params = {}
        view = sublime.active_window().active_view()
        # Save file to disk
        view.run_command("save")

        # Get mouse cursor position from event
        point = view.sel()[0].begin() if event is None else view.window_to_text((event["x"], event["y"]))
        current_pos = view.rowcol(point)
        line, col = current_pos[0] + 1, current_pos[1] + 1
        project_files = get_project_files()
        path = current_path()

        is_symbol_res = is_symbol(path, project_files, line, col)
        if not is_symbol_res["exists"]:
            log_info("Target is not a valid symbol")
            view.show_popup("Can't rename symbol")
        else:
            self.params = {
                "path": current_path(),
                "line": line,
                "col": col,
                "projectFiles": get_project_files()
            }
            self.window.show_input_panel("Rename symbol:", is_symbol_res["name"], self.on_done, None, None)

    def on_done(self, text):
        rename_thread = RenameThread(rename_complete, self.params.get("path"), self.params.get("projectFiles"),
                                     text,
                                     self.params.get("line"),
                                     self.params.get("col"))

        rename_thread.start()

    def want_event(self):
        return True
