import os
import scrollphathd
import psutil
from argparse import ArgumentParser
try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty
from action import Action
from stoppablethread import StoppableThread
try:
    import http.client as http_status
except ImportError:
    import httplib as http_status
from flask import Blueprint, render_template, abort, request, jsonify, Flask
import time, threading
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

scrollphathd_blueprint = Blueprint('scrollhat', __name__)
api_queue = Queue()

class AutoScroll():
    _is_enabled = False
    _interval = 0.1

    def config(self, is_enabled="False", interval=0.1):
        self._interval = interval

        if is_enabled == "True":
            if self._is_enabled is False:
                self._is_enabled = True
                self.run()
        else:
            self._is_enabled = False

    def run(self):
        if self._is_enabled is True:
            # Start a timer
            threading.Timer(self._interval, self.run).start()
            # Scroll the buffer content
            scrollphathd.scroll()
            # Show the buffer
            scrollphathd.show()

class State():
    _current_action = ''
    _scheduler = BackgroundScheduler()

    def get_current_action(self):
        return self._current_action

    def set_current_action(self, proc):
        self._current_action = proc

    def get_scheduler(self):
        return self._scheduler

@scrollphathd_blueprint.route('/autoscroll', methods=["POST"])
def autoscroll():
    response = {"result": "success"}
    status_code = http_status.OK

    data = request.get_json()
    if data is None:
        data = request.form
    try:
        api_queue.put(Action("autoscroll", (data["is_enabled"], float(data["interval"]))))
    except KeyError:
        response = {"result": "KeyError", "error": "keys is_enabled and interval not posted."}
        status_code = http_status.UNPROCESSABLE_ENTITY
    except ValueError:
        response = {"result": "ValueError", "error": "invalid data type(s)."}
        status_code = http_status.UNPROCESSABLE_ENTITY

    return jsonify(response), status_code


@scrollphathd_blueprint.route('/scroll', methods=["POST"])
def scroll():
    response = {"result": "success"}
    status_code = http_status.OK

    data = request.get_json()
    if data is None:
        data = request.form
    try:
        api_queue.put(Action("scroll", (int(data["x"]), int(data["y"]))))
    except KeyError:
        response = {"result": "KeyError", "error": "keys x and y not posted."}
        status_code = http_status.UNPROCESSABLE_ENTITY
    except ValueError:
        response = {"result": "ValueError", "error": "invalid integer."}
        status_code = http_status.UNPROCESSABLE_ENTITY

    return jsonify(response), status_code


@scrollphathd_blueprint.route('/show', methods=["POST"])
def show():
    response = {"result": "success"}
    status_code = http_status.OK

    data = request.get_json()
    if data is None:
        data = request.form
    try:
        api_queue.put(Action("write", data["text"]))
    except KeyError:
        response = {"result": "KeyError", "error": "key 'text' not set"}
        status_code = http_status.UNPROCESSABLE_ENTITY

    return jsonify(response), status_code


@scrollphathd_blueprint.route('/clear', methods=["POST"])
def clear():
    response = {"result": "success"}
    status_code = http_status.OK

    api_queue.put(Action("clear", {}))
    return jsonify(response), status_code

@scrollphathd_blueprint.route('/clearwater', methods=["POST"])
def clearwater():
    response = {"result": "success"}
    status_code = http_status.OK

    api_queue.put(Action("clearwater", {}))
    return jsonify(response), status_code


@scrollphathd_blueprint.route('/flip', methods=["POST"])
def flip():
    response = {"result": "success"}
    status_code = http_status.OK

    data = request.get_json()
    if data is None:
        data = request.form
    try:
        api_queue.put(Action("flip", (bool(data["x"]), bool(data["y"]))))
    except TypeError:
        response = {"result": "TypeError", "error": "Could not cast data correctly. Both `x` and `y` must be set to true or false."}
        status_code = http_status.UNPROCESSABLE_ENTITY
    except KeyError:
        response = {"result": "KeyError", "error": "Could not cast data correctly. Both `x` and `y` must be in the posted json data."}
        status_code = http_status.UNPROCESSABLE_ENTITY

    return jsonify(response), status_code

@scrollphathd_blueprint.route('/full', methods=["POST"])
def full():
    response = {"result": "success"}
    status_code = http_status.OK

    api_queue.put(Action("full", {}))

    return jsonify(response), status_code

@scrollphathd_blueprint.route('/custom', methods=["POST"])
def custom():
    response = {"result": "success"}
    status_code = http_status.OK

    data = request.get_json()
    if data is None:
        data = request.form
    try:
        api_queue.put(Action("custom", data['custom']))
    except TypeError:
        response = {"result": "TypeError", "error": "Could not cast data correctly. An option must be selected."}
        status_code = http_status.UNPROCESSABLE_ENTITY
    except KeyError:
        response = {"result": "KeyError", "error": "Could not cast data correctly. Custom option must be in the posted json data."}
        status_code = http_status.UNPROCESSABLE_ENTITY

    return jsonify(response), status_code

@scrollphathd_blueprint.route('/water', methods=["POST"])
def water():
    response = {"result": "success"}
    status_code = http_status.OK

    data = request.get_json()
    if data is None:
        data = request.form
    try:
        api_queue.put(Action("water", data['water']))
    except TypeError:
        response = {"result": "TypeError", "error": "Could not cast water correctly. An interval must be selected."}
        status_code = http_status.UNPROCESSABLE_ENTITY
    except KeyError:
        response = {"result": "KeyError", "error": "Could not cast water correctly. Custom option must be in the posted json data."}
        status_code = http_status.UNPROCESSABLE_ENTITY

    return jsonify(response), status_code

def start_background_thread():
    api_thread = StoppableThread(target=run)
    api_thread.start()

def full_board():
    # Fills with pixels the whole board
    for x in range(17):
        for y in range(7):
            scrollphathd.set_pixel(x, y, 1)

def cleanup():
    # Reset the autoscroll
    autoscroll.config()
    # Clear the buffer before writing new text
    scrollphathd.clear()
    # Kill active subprocess
    kill_subthread()

def kill_subthread():
    if len(state.get_current_action()) > 0:
        for proc in psutil.process_iter():
            # check whether the process name matches
            if len(proc.cmdline()) > 1 and str(state.get_current_action()) in proc.cmdline()[1]:
                print('{} process killed x_x'.format(proc))
                proc.kill()
                state.set_current_action(None)

def set_reminder(interval):
    state.get_scheduler().pause()
    state.get_scheduler().remove_job('water_reminder')
    state.get_scheduler().add_job(func=water_reminder, trigger="interval", seconds=(int(interval) * 60), id='water_reminder')
    state.get_scheduler().resume()

def water_reminder():
    print('water reminder')
    prev_action = state.get_current_action()
    api_queue.put(Action("write", 'H2O time! :D '))
    api_queue.put(Action("autoscroll", (u'True', 0.1)))
    StoppableThread(target=clean_reminder,args=[prev_action]).start()

def clean_reminder(prev_action):
    time.sleep(15)
    if prev_action is not None and '.py' in prev_action:
        api_queue.put(Action("custom", prev_action[:-3])) # Get rid off the .py extension
    elif prev_action is not None and '.py' not in prev_action:
        api_queue.put(Action("write", prev_action))
        api_queue.put(Action("autoscroll", (u'True', 0.1)))
    else:
        print('there was no prev action')
    #StoppableThread(target=clean_reminder).join()

def run():
    while True:
        action = api_queue.get(block=True)

        if action.action_type == "write":
            cleanup()
            state.set_current_action(action.data)
            scrollphathd.write_string(action.data)
            scrollphathd.scroll(0, -1)

        if action.action_type == "clear":
            cleanup()

        if action.action_type == "clearwater":
            cleanup()
            state.get_scheduler().remove_job('water_reminder')

        if action.action_type == "scroll":
            scrollphathd.scroll(action.data[0], action.data[1])

        if action.action_type == "flip":
            scrollphathd.flip(x=action.data[0], y=action.data[1])

        if action.action_type == "autoscroll":
            autoscroll.config(action.data[0], action.data[1])

        if action.action_type == "custom":
            cleanup()
            state.set_current_action('{}.py'.format(action.data))
            os.system('python ./patterns/{}.py &'.format(action.data))

        if action.action_type == "full":
            cleanup()
            full_board()

        if action.action_type == "water":
            set_reminder(action.data)

        scrollphathd.show()

@atexit.register
def stop_background_thread():
    state.get_scheduler().shutdown(wait=False)
    api_thread = StoppableThread(target=run)
    api_thread.stop()
    print('bye fella')

scrollphathd_blueprint.before_app_first_request(start_background_thread)

# Autoscroll handling
autoscroll = AutoScroll()
state = State()
state.get_scheduler().add_job(func=water_reminder, trigger="interval", seconds=0, id='water_reminder')
state.get_scheduler().start(paused=True)

def main():
    # Parser handling
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", type=int, help="HTTP port.", default=8080)
    parser.add_argument("-H", "--host", type=str, help="HTTP host.", default="0.0.0.0")
    args = parser.parse_args()

    # TODO Check
    scrollphathd.set_clear_on_exit(False)
    scrollphathd.write_string(str(args.port), x=1, y=1, brightness=0.1)
    scrollphathd.show()

    # Flash usage
    app = Flask(__name__)
    app.register_blueprint(scrollphathd_blueprint, url_prefix="/scrollphathd")

    app.run(port=args.port, host=args.host)
    cleanup()
    # Shut down the scheduler when exiting the app
    state.get_scheduler().shutdown()


if __name__ == '__main__':
    main()
