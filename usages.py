from .server import *

import sublime
import sublime_plugin


def find_usages(path, context_path, project_files, line, col):
    res = post_request("find-usages", {
        "line": line,
        "col": col,
        "path": path,
        "context": context_path,
        "projectFiles": project_files
    })

    if not res["success"]:
        log_error("Find usages failed with error - {}:{}".format(res.get("error"), res.get("errorMessage")))
        return None

    if "body" not in res:
        log_error("Bad JSON for find_usages: no body")
        return None

    return res["body"]


def show_output_panel(name: str, contents: str):
    win = sublime.active_window()
    panel = win.create_output_panel(name)
    panel.set_syntax_file("Packages/Default/Find Results.hidden-tmLanguage")
    panel.settings().set("result_file_regex", "^([^\\s]+\\.\\w+):?(\\d+)?")
    panel.settings().set("result_line_regex", "  (\\d+):")
    win.run_command('show_panel', {"panel": "output." + name})
    panel.run_command("append", {"characters": contents})


def group_usages(usages):
    result_map = {}
    for file in usages:
        prev_line = None
        groups = []

        for pos in usages[file]:
            line = pos[0]
            if prev_line is not None and line - prev_line < USAGE_GROUP_THRESHHOLD:
                groups[-1].append(line)
            else:
                groups.append([line])
            prev_line = line

        result_map[file] = groups
    return result_map


def build_usage_panel_contents(usage_groups, num_usages=0):
    log_info("build_usage_panel_contents len={}".format(len(usage_groups)))
    if len(usage_groups) == 0:
        log_info("Found no usages - showing to user")
        return "No usages found\n"

    contents = "Found {} usage{}\n".format(num_usages, "s" if num_usages > 1 else "")

    view = sublime.active_window().active_view()

    for file in usage_groups:
        contents += "{}:\n".format(file)

        lines = []
        path = file
        if file == view.file_name():
            path = tempfile.gettempdir() + "/PerlComplete.pl"

        if not os.path.exists(path):
            log_error("Find usages: File {} does not exist".format(file))
            continue
        else:
            lines = open(path, encoding="utf-8").read().splitlines()

        # Find largest line number in group so we can align the sidebar line numbers
        line_num_digits = len(str(usage_groups[file][-1][-1]))

        for group in usage_groups[file]:
            # Figure out what lines to list
            lines_to_show = []
            if group[0] > 2 and group[0] - 2 not in lines_to_show:
                lines_to_show.append(group[0] - 2)

            if group[0] > 1 and group[0] - 1 not in lines_to_show:
                lines_to_show.append(group[0] - 1)

            # Now include every line in the group
            for i in range(group[0], group[-1] + 1):
                if i not in lines_to_show:
                    lines_to_show.append(i)

            # Finally add some context lines after the match
            if group[-1] + 1 < len(lines) and group[-1] + 1 not in lines_to_show:
                lines_to_show.append(group[-1] + 1)
            if group[-1] + 2 < len(lines) and group[-1] + 2 not in lines_to_show:
                lines_to_show.append(group[-1] + 2)

            # Now we can add the group to the file
            contents += "  {} \n".format("." * line_num_digits)

            for line in lines_to_show:
                # If the line number length is less than the largest line number length, additional padding is needed
                # to ensure all lines are aligned
                padding_size = 2 + (line_num_digits - len(str(line)))
                padding_size += (0 if line in group else 1)
                padding = " " * padding_size;
                source_line = lines[line - 1]
                colon = ":" if line in group else ""
                contents += "  {}{}{}{}\n".format(line, colon, padding, source_line)

    return contents


class FindUsagesCommand(sublime_plugin.TextCommand):
    def run(self, edit, event=None):
        point = self.view.sel()[0].begin() if event is None else self.view.window_to_text((event["x"], event["y"]))

        current_pos = self.view.rowcol(point)
        file_data_path = write_buffer_to_file(self.view)
        current_path = self.view.window().active_view().file_name()

        find_usage_thread = FindUsageThread(on_usages_complete, file_data_path, current_path, get_project_files(),
                                            current_pos[0] + 1,
                                            current_pos[1] + 1)

        show_output_panel(USAGES_PANEL_NAME, "Finding usages...")

        find_usage_thread.start()

    def want_event(self):
        # Force sublime to get event from click
        # This allows us to get right click location
        return True


def on_usages_complete(usages):
    if usages is None:
        log_error("Failed to get usages - error returned")
        return

    usage_groups = group_usages(usages)
    num_usages = 0
    for file in usages:
        num_usages += len(usages[file])

    log_debug("Found usages - {}".format(usage_groups))
    show_output_panel(USAGES_PANEL_NAME, build_usage_panel_contents(usage_groups, num_usages))


class FindUsageThread(threading.Thread):

    def __init__(self, on_complete, path, context_path, project_files, line, col):
        super(FindUsageThread, self).__init__()
        self.path = path
        self.context_path = context_path
        self.line = line
        self.col = col
        self.on_complete = on_complete
        self.project_files = project_files

    def run(self):
        self.on_complete(find_usages(self.path, self.context_path, self.project_files, self.line, self.col))
