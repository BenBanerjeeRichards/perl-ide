from .util import *
from .server import *
import sublime
import sublime_plugin
import threading

# Allow restarting server
AUTO_RESTART = True


class StartServerThread(threading.Thread):
    def __init__(self, on_started):
        super(StartServerThread, self).__init__()
        self.on_started = on_started

    def run(self):
        if not ping():
            if not AUTO_RESTART:
                self.on_started(False)
                return
            log_debug("Server stopped - starting again")
            # Could not connect to server, needs to be started
            # First stop any PerlParser processes that may be lying around for some reason
            stop_server()
            os.system("nohup \"" + get_exe_path() + "\" serve &")
            # Wait for serve to come up
            start = time.time()
            while not ping():
                diff = time.time() - start
                # give up after a second
                if diff > 1:
                    log_error("Server didn't start within one second")
                    self.on_started(False)
                    return
        else:
            log_debug("Server already running")

        self.on_started(True)


def index_project(project_files):
    res = post_request("index-project", {"projectFiles": project_files})
    return res


def on_index_complete(res):
    log_info("Indexing complete, res = {}".format(res))
    set_status(STATUS_READY)


def on_server_started(success):
    if not success:
        set_status(STATUS_STOPPED)
        return

    # Index project
    set_status(STATUS_INDEXING)
    indexer = IndexProjectThread(on_index_complete, get_project_files())
    indexer.start()


class IndexProjectThread(threading.Thread):

    def __init__(self, on_complete, project_files):
        super(IndexProjectThread, self).__init__()
        self.project_files = project_files
        self.on_complete = on_complete

    def run(self):
        log_debug("Indexing project...")
        self.on_complete(index_project(self.project_files))


class PerlIdeListener(sublime_plugin.EventListener):

    def __init__(self):
        pass

    def on_activated(self, view):
        log_info("Loaded Perl_IDE")
        set_status("", view)
        if not os_supported():
            set_status(STATUS_OS_NOT_SUPPORTED, view)
            return
        if not arch_supported():
            set_status(STATUS_ARCH_NOT_SUPPORTED, view)
            return

        update_menu()
        if not current_view_is_perl():
            return
        else:
            set_status(STATUS_ON_LOAD, view)
            log_info("Loaded perl file, checking server")
            start_server_thread = StartServerThread(on_server_started)
            start_server_thread.start()


# Command to move cursor to specific position in current view
class MoveCursorCommand(sublime_plugin.TextCommand):
    def run(self, edit, line, col, path):
        sublime.active_window().open_file("{}:{}:{}".format(path, line, col), sublime.ENCODED_POSITION)


class ReloadServerCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        log_info("Restarting server")
        stop_server()
        start_server()


configure_settings()
update_menu()
