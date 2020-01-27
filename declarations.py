from .server import *
import sublime
import sublime_plugin


def find_declaration(path, context_path, line, col):
    res = post_request("find-declaration", {
        "line": line,
        "col": col,
        "path": path,
        "context": context_path,
        "projectFiles": get_project_files()
    })

    if not res["success"]:
        log_error("Find declaration failed with error - {}:{}".format(res.get("error"), res.get("errorMessage")))
        return None

    if "body" not in res:
        log_error("Bad JSON for find_declaration: no body")
        return None

    return res["body"]


def get_source_line(view, line_regions, line):
    if line >= len(line_regions):
        return None

    return view.substr(line_regions[line - 1])


class GotoDeclarationCommand(sublime_plugin.TextCommand):
    def run(self, edit, event=None):
        point = self.view.sel()[0].begin() if event is None else self.view.window_to_text((event["x"], event["y"]))
        current_pos = self.view.rowcol(point)
        file_data_path = write_buffer_to_file(self.view)
        current_path = self.view.window().active_view().file_name()

        find_decl_thread = GotoDeclarationThread(on_find_declaration_complete, file_data_path, current_path,
                                                 current_pos[0] + 1, current_pos[1] + 1)

        find_decl_thread.start()

    def want_event(self):
        # Force sublime to get event from click
        # This allows us to get right click location
        return True


class GotoDeclarationThread(threading.Thread):

    def __init__(self, on_complete, path, context_path, line, col):
        super(GotoDeclarationThread, self).__init__()
        self.path = path
        self.context_path = context_path
        self.line = line
        self.col = col
        self.on_complete = on_complete

    def run(self):
        self.on_complete(find_declaration(self.path, self.context_path, self.line, self.col))


def on_find_declaration_complete(declaration):
    log_info("Declaration returned {}".format(declaration))
    view = sublime.active_window().active_view()

    if declaration is not None and declaration["exists"]:
        # Move the cursor
        # Have to use event as we can't change cursor position in this thread
        sublime.active_window().run_command("move_cursor", {"line": declaration["line"], "col": declaration["col"],
                                                            "path": declaration["file"]})
    else:
        view.show_popup("Declaration not found")
