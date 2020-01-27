import sublime
import sublime_plugin
import threading
import random
from .main import *

def index_project(project_files):
    res = post_request("index-project", {"projectFiles": project_files})
    return res

def get_completions(complete_type, params, word_separators):
    params["projectFiles"] = get_project_files()
    res = post_request(complete_type, params)
    if not res["success"]:
        log_error("Completions failed with error - {}:{}".format(res.get("error"), res.get("errorMessage")))
        return []

    # Convert (completion, detail) to (completion + "\t" + detail, "")
    # In sublime the tab deliminates the two parts
    completions = []
    for completion in res["body"]:
        replacement = completion[0]
        if not replacement:
            continue

        if replacement[0] == "$":
            replacement = "\\" + replacement

        completions.append((completion[0] + "\t" + completion[1], replacement))

    log_info(completions)
    return completions


class IndexProjectThread(threading.Thread):

    def __init__(self, on_complete, project_files):
        super(IndexProjectThread, self).__init__()
        self.project_files = project_files
        self.on_complete = on_complete

    def run(self):
        log_info("Indexing project...")
        self.on_complete(index_project(self.project_files))


# To python, our autocomplete request is just an IO operation (network operation)
# So as soon as our thread starts, it will go into blocked state and so GIL will return control to
# sublime text
class AutoCompleterThread(threading.Thread):
    def __init__(self, on_complete, job_id, complete_type, complete_params, word_separators):
        super(AutoCompleterThread, self).__init__()
        self.on_complete = on_complete
        self.job_id = job_id

        self.complete_params = complete_params
        self.complete_type = complete_type
        self.word_separators = word_separators

    def run(self):
        completions = get_completions(self.complete_type, self.complete_params, self.word_separators)
        self.on_complete(self.job_id, completions)


class PerlCompletionsListener(sublime_plugin.EventListener):

    def __init__(self):
        self.completions = None
        self.latest_completion_job_id = None

        # If autocomplete for a specific file
        self.use_async = True

    def on_query_completions(self, view, prefix, locations):
        if not plugin_supported():
            return

        # TODO move this elsewhere
        view.settings().set("word_separators", "./\\()\"'-,.;<>~!@#$%^&*|+=[]{}`~?")
        # Disable on non-perl files
        if view.settings().get("syntax") != "Packages/Perl/Perl.sublime-syntax":
            set_status("", view)
            return

        # We have a result from the autocomplete thread
        if self.completions:
            set_status(STATUS_READY, view)
            completion_cpy = self.completions.copy()
            self.completions = None
            return (completion_cpy, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

        if self.completions == []:
            # Empty list means no completions, don't try to do any more
            self.completions = None
            return None

        word_separators = view.settings().get("word_separators")
        current_path = view.window().active_view().file_name()
        # Write current (unsaved) file to a file
        file_data_path = write_buffer_to_file(view)
        current_pos = view.rowcol(view.sel()[0].begin())
        current_pos = (current_pos[0] + 1, current_pos[1] + 1)
        sigil = view.substr(view.line(view.sel()[0]))

        autocomplete_method = COMPLETE_VAR
        complete_params = {"line": current_pos[0], "col": current_pos[1], "path": file_data_path,
                           "context": current_path}

        if not sigil or not (sigil[-1] == "$" or sigil[-1] == '@' or sigil[-1] == '%'):
            complete_method = COMPLETE_SUB
        else:
            complete_params["sigil"] = sigil[-1]
            complete_method = COMPLETE_VAR

        set_status(STATUS_LOADING, view)
        job_id = random.randint(1, 100000)
        completion_thread = AutoCompleterThread(self.on_completions_done, job_id, complete_method, complete_params,
                                                word_separators)
        log_info("Starting autocomplete thread with job id {}".format(job_id))
        self.latest_completion_job_id = job_id
        completion_thread.start()

        return ([], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

    def on_activated(self, view):
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
            print("LOAD PERL")
            set_status(STATUS_ON_LOAD, view)
            log_info("Loaded perl file, checking server")
            start_server()
            if ping():
                set_status(STATUS_READY, view)
            else:
                set_status(STATUS_STOPPED, view)
                return

            # Indexing project
            set_status(STATUS_INDEXING, view)
            indexer = IndexProjectThread(self.on_index_complete, get_project_files())
            indexer.start()

    def on_index_complete(self, res):
        log_info("Indexing complete, res = {}".format(res))
        set_status(STATUS_READY)

    def on_completions_done(self, job_id, completions):
        log_info("Autocomplete job #{} with completions = {}".format(job_id, completions))
        if job_id != self.latest_completion_job_id:
            log_info("Discarding completion result as job is old: job_id = {}, latest_job_id={}".format(job_id,
                                                                                                        self.latest_completion_job_id))
            return

        self.completions = completions
        view = sublime.active_window().active_view()

        # Hide existing autocomplete popup and retrigger on_query_completions
        view.run_command('hide_auto_complete')
        view.run_command('auto_complete', {
            'disable_auto_insert': True,
            'api_completions_only': False,
            'next_competion_if_showing': False})
