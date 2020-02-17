import sublime
import sublime_plugin
import platform
import os
import json
import tempfile

PERL_COMPLETE_SERVER = "http://localhost:1234/"

# Constants for the status bar
STATUS_KEY = "perl_complete"
STATUS_READY = "Perl IDE ✔"
STATUS_STOPPED = "Perl IDE ✖ - Language server not found"
STATUS_OS_NOT_SUPPORTED = "Perl IDE ✖ - OS not supported"
STATUS_ARCH_NOT_SUPPORTED = "Perl IDE ✖ - Architecture not supported"
STATUS_LOADING = "Perl IDE ..."
STATUS_INDEXING = "Perl IDE ... [Indexing Project]"
STATUS_ON_LOAD = "Perl IDE"
debug = False
info = False

COMPLETE_SUB = "autocomplete-sub"
COMPLETE_VAR = "autocomplete-var"

POST_ATTEMPTS = 5

# Number of lines difference to split groups in find UX
USAGE_GROUP_THRESHHOLD = 5
USAGES_PANEL_NAME = "usages"


def log_info(msg):
    if info:
        print("[P_IDE:INFO] - {}".format(msg))


def log_error(msg):
    print("[P_IDE:ERRO] - {}".format(msg))


def log_debug(msg):
    if debug:
        print("[P_IDE:DEBG] - {}".format(msg))


def set_status(status, view=None):
    if view is None:
        view = sublime.active_window().active_view()
    view.set_status(STATUS_KEY, "")
    view.set_status(STATUS_KEY, status)


def configure_settings():
    settings = sublime.load_settings("Preferences.sublime-settings")
    auto_complete_triggers = settings.get("auto_complete_triggers")
    auto_complete_triggers = [] if auto_complete_triggers is None else auto_complete_triggers

    found = False
    for trigger in auto_complete_triggers:
        if trigger["selector"] == "source.perl":
            found = True
            trigger["characters"] = "$%@"

    if not found:
        auto_complete_triggers.append({"selector": "source.perl", "characters": "$@%"})

    settings.set("auto_complete_triggers", auto_complete_triggers)
    sublime.save_settings("Preferences.sublime-settings")


def get_project_files():
    # Get or guess project files
    if sublime.active_window().project_file_name() is None:
        # No project loaded
        current_path = sublime.active_window().active_view().file_name()
        source_dir = os.path.dirname(current_path)
        perl_files = []
        for file in os.listdir(source_dir):
            if file.endswith(".pl") or file.endswith(".pm"):
                perl_files.append(source_dir + "/" + file)

        return perl_files
    else:
        # TODO project files
        return []


def os_supported():
    plt = platform.system().lower()
    if plt not in ["darwin", "linux"]:
        return False

    return True


def arch_supported():
    return platform.machine() == "x86_64"


def plugin_supported():
    return os_supported() and arch_supported()


def write_buffer_to_file(view):
    path = tempfile.gettempdir() + "/PerlComplete.pl"
    with open(path, "w+", encoding="utf-8") as f:
        f.write(view.substr(sublime.Region(0, view.size())))

    return path


def current_view_is_perl():
    current_view = sublime.active_window().active_view()
    return current_view.settings().get("syntax") == "Packages/Perl/Perl.sublime-syntax"


def update_menu():
    # If current view is a perl file, then show the Find Usages in the context menu
    file_path_context = os.path.abspath(os.path.join(os.path.dirname(__file__), "Context.sublime-menu"))

    menu = []
    if current_view_is_perl():
        menu = [{"caption": "-"}, {"caption": "Find Usages", "command": "find_usages"},
                {"caption": "Goto Declaration", "command": "goto_declaration"},
                {"caption": "Rename...", "command": "rename_symbol"}, {"caption": "-"}, ]

    with open(file_path_context, "w+") as f:
        f.write(json.dumps(menu))


def current_path():
    return sublime.active_window().active_view().file_name()
