from .util import *
from .server import *
import sublime
import sublime_plugin
import threading


def index_project(project_files):
    res = post_request("index-project", {"projectFiles": project_files})
    return res


class IndexProjectThread(threading.Thread):

    def __init__(self, on_complete, project_files):
        super(IndexProjectThread, self).__init__()
        self.project_files = project_files
        self.on_complete = on_complete

    def run(self):
        log_info("Indexing project...")
        self.on_complete(index_project(self.project_files))


class PerlIdeListener(sublime_plugin.EventListener):

    def __init__(self):
        pass

    def on_activated(self, view):
        print("NEW LOAD")
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
            start_server()
            if ping():
                set_status(STATUS_READY, view)
            else:
                set_status(STATUS_STOPPED, view)
                return

            # Index project
            set_status(STATUS_INDEXING, view)
            indexer = IndexProjectThread(self.on_index_complete, get_project_files())
            indexer.start()

    def on_index_complete(self, res):
        log_info("Indexing complete, res = {}".format(res))
        set_status(STATUS_READY)
