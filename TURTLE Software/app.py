from flask import Flask, request, jsonify, render_template_string, send_from_directory
import serial
import time
import json
import os
import RPi.GPIO as GPIO
import ImageGrabAndSave

# -------------------------
# Settings
# -------------------------

PICO_PORT = "/dev/ttyACM0"
PICO_BAUD = 115200

LASER_1_GPIO = 23
LASER_2_GPIO = 24
LED_GPIO = 25

FILTER_STEPS_PER_MOTOR_ROTATION = 2048
FILTER_DELAY_US = 1500
FILTER_POWER = 80

# The app assumes the wheel starts on Filter 1
current_filter = 1

# -------------------------
# GPIO setup
# -------------------------

GPIO.setmode(GPIO.BCM)

GPIO.setup(LASER_1_GPIO, GPIO.OUT)
GPIO.setup(LASER_2_GPIO, GPIO.OUT)
GPIO.setup(LED_GPIO, GPIO.OUT)

GPIO.output(LASER_1_GPIO, GPIO.LOW)
GPIO.output(LASER_2_GPIO, GPIO.LOW)
GPIO.output(LED_GPIO, GPIO.LOW)

# -------------------------
# Serial setup
# -------------------------

pico = None
APP_DIR = os.path.dirname(os.path.abspath(__file__))


def connect_pico():
    global pico

    if pico is not None and pico.is_open:
        return pico

    pico = serial.Serial(PICO_PORT, PICO_BAUD, timeout=3)
    time.sleep(2)
    pico.reset_input_buffer()

    return pico


def send_to_pico(command):
    ser = connect_pico()

    line = command + "\r\n"
    ser.write(line.encode("utf-8"))

    response = ser.readline().decode("utf-8", errors="ignore").strip()

    if response:
        return response

    return "No response from Pico"


def send_to_pico_no_wait(command):
    ser = connect_pico()

    line = command + "\r\n"
    ser.write(line.encode("utf-8"))

    return "sent"


def move_filter_to(target_filter, delay_us=FILTER_DELAY_US):
    global current_filter

    target_filter = int(target_filter)

    if target_filter < 1 or target_filter > 4:
        return {
            "ok": False,
            "error": "Invalid filter number",
            "target_filter": target_filter
        }

    previous_filter = current_filter
    rotations = target_filter - current_filter
    steps = rotations * FILTER_STEPS_PER_MOTOR_ROTATION

    if steps == 0:
        return {
            "ok": True,
            "message": "Already at requested filter",
            "previous_filter": previous_filter,
            "current_filter": current_filter,
            "target_filter": target_filter,
            "rotations": 0,
            "steps": 0
        }

    command = {
        "cmd": "move",
        "axis": "filter",
        "steps": steps,
        "delay_us": int(delay_us),
        "power": FILTER_POWER
    }

    response = send_to_pico(json.dumps(command))

    try:
        pico_data = json.loads(response)

        if pico_data.get("ok") is True:
            current_filter = target_filter

    except Exception:
        pass

    return {
        "ok": True,
        "previous_filter": previous_filter,
        "current_filter": current_filter,
        "target_filter": target_filter,
        "rotations": rotations,
        "steps": steps,
        "sent": command,
        "pico_response": response
    }

# -------------------------
# Flask app
# -------------------------

app = Flask(__name__)


@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(APP_DIR, filename, conditional=True)

dir = os.path.dirname(__file__)
filename = os.path.join(dir, "Interface.html")

HtmlFile = open(filename, 'r', encoding='utf-8')
source_code = HtmlFile.read() 

HTML_PAGE = source_code


@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app.route("/api/stepper", methods=["POST"])
def api_stepper():
    data = request.json

    axis = data.get("axis", "x")
    steps = int(data.get("steps", 100))
    delay_us = int(data.get("delay_us", 2000))
    power = int(data.get("power", 70))

    command = {
        "cmd": "move",
        "axis": axis,
        "steps": steps,
        "delay_us": delay_us,
        "power": power
    }

    response = send_to_pico(json.dumps(command))

    return jsonify({
        "sent": command,
        "pico_response": response
    })


@app.route("/api/jog", methods=["POST"])
def api_jog():
    data = request.json

    axis = data.get("axis", "x")
    direction = int(data.get("direction", 1))
    delay_us = int(data.get("delay_us", 2000))
    power = int(data.get("power", 70))

    command = {
        "cmd": "jog",
        "axis": axis,
        "direction": direction,
        "delay_us": delay_us,
        "power": power
    }

    response = send_to_pico_no_wait(json.dumps(command))

    return jsonify({
        "sent": command,
        "response": response
    })


@app.route("/api/move_xy", methods=["POST"])
def api_move_xy():
    data = request.json

    x_steps = int(data.get("x_steps", 0))
    y_steps = int(data.get("y_steps", 0))
    delay_us = int(data.get("delay_us", 3000))
    power = int(data.get("power", 70))

    command = {
        "cmd": "move_xy",
        "x_steps": x_steps,
        "y_steps": y_steps,
        "delay_us": delay_us,
        "power": power
    }

    response = send_to_pico(json.dumps(command))

    return jsonify({
        "sent": command,
        "pico_response": response
    })

@app.route("/api/state", methods=["GET"])
def api_state():
    command = {"cmd": "state"}
    response = send_to_pico(json.dumps(command))

    try:
        return jsonify(json.loads(response))
    except Exception:
        return jsonify({
            "ok": False,
            "pico_response": response
        })

@app.route("/api/home", methods=["POST"])
def api_home():
    data = request.json or {}

    delay_us = int(data.get("delay_us", 2000))
    power = int(data.get("power", 80))

    command = {
        "cmd": "home",
        "delay_us": delay_us,
        "power": power
    }

    response = send_to_pico(json.dumps(command))

    return jsonify({
        "sent": command,
        "pico_response": response
    })

@app.route("/api/filter", methods=["POST"])
def api_filter():
    data = request.json

    target_filter = int(data.get("filter", 1))
    delay_us = int(data.get("delay_us", FILTER_DELAY_US))

    result = move_filter_to(target_filter, delay_us)

    return jsonify(result)


@app.route("/api/stop", methods=["POST"])
def api_stop():
    command = {"cmd": "stop"}
    response = send_to_pico(json.dumps(command))

    return jsonify({
        "sent": command,
        "pico_response": response
    })


@app.route("/api/release", methods=["POST"])
def api_release():
    command = {"cmd": "release"}
    response = send_to_pico(json.dumps(command))

    return jsonify({
        "sent": command,
        "pico_response": response
    })


@app.route("/api/servo", methods=["POST"])
def api_servo():
    data = request.json
    angle = int(data.get("angle", 90))

    command = {
        "cmd": "servo",
        "angle": angle
    }

    response = send_to_pico(json.dumps(command))

    return jsonify({
        "sent": command,
        "pico_response": response
    })


@app.route("/api/light", methods=["POST"])
def api_light():
    data = request.json

    light = data.get("light", "")
    state = bool(data.get("state", False))

    if light == "laser1":
        pin = LASER_1_GPIO
    elif light == "laser2":
        pin = LASER_2_GPIO
    elif light == "led":
        pin = LED_GPIO
    else:
        return jsonify({"error": "Invalid light source"}), 400

    GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)

    return jsonify({
        "light": light,
        "state": "ON" if state else "OFF"
    })

@app.route("/api/pictures", methods=["POST"])
def api_pictures():
    data = request.json

    filename = data.get("filename", "")
    output_type = data.get("output_type", "PNG")

    output_type_list = ["raw", "JPEG", "BMP", "TIFF", "PNG"]

    if output_type not in output_type_list:
        return jsonify({"error": "Invalid output type"}), 400
    else: 
        output_type_index = output_type_list.index(output_type)

    succes = ImageGrabAndSave.capture_single_image(output_type_index, filename)

    return jsonify({
        "filename": filename,
        "output_type": output_type,
        "success": succes
    })
    
    

if __name__ == "__main__":
    try:
        connect_pico()
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

    finally:
        try:
            print("Returning stage to origin...")
            command = {
                "cmd": "home",
                "delay_us": 2000,
                "power": 80
            }
            send_to_pico(json.dumps(command))
        except Exception as e:
            print("Could not return stage to origin:", e)

        try:
            print("Returning filter wheel to Filter 1...")
            move_filter_to(1, FILTER_DELAY_US)
        except Exception as e:
            print("Could not return filter wheel to Filter 1:", e)

        GPIO.cleanup()
