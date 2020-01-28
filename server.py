import threading
import platform
import urllib
import time
from .util import *

def post_request(method, params, attempts=0):
    if attempts > POST_ATTEMPTS:
        log_error("Failed to connect to complete server after 5 attempts")
        return
    try:
        log_debug("Running command method={} params={}".format(method, params))
        post_data = {
            "method": method,
            "params": params
        }

        req = urllib.request.Request(PERL_COMPLETE_SERVER)
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        post_json = json.dumps(post_data).encode("utf-8")
        req.add_header('Content-Length', len(post_json))
        res = urllib.request.urlopen(req, post_json)
        return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8"))
    except urllib.error.URLError as e:
        log_error("Failed to connect to CompleteServer - starting and retrying: {}".format(e))
        start_server()
        return post_request(method, params, attempts + 1)


def get_exe_path():
    print("GET_EXE_PATH")
    plat = platform.system().lower()
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    lib_path = os.path.join(script_dir, "lib")
    if plat == "darwin":
        # macos
        return os.path.join(lib_path, "perlparser-mac")
    elif plat == "linux":
        return os.path.join(lib_path, "perlparser-linux")

    log_error("Could not find path for OS")
    return None


def stop_server():
    os.system("killall -9 PerlParser")


def start_server():
    pass


def ping():
    try:
        urllib.request.urlopen(PERL_COMPLETE_SERVER + "ping").read()
    except urllib.error.HTTPError:
        return True  # Bad ping behaviour but at least the server is running
    except urllib.error.URLError:
        return False

    return True
