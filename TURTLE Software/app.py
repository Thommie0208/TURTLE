from flask import Flask, request, jsonify, render_template_string
import serial
import time
import json
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


HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>TURTLE Interface</title>
    <style>
    body {
        margin: 0;
        font-family: Arial, sans-serif;
        background: #efefef;
        color: black;
        width: 100vw;
        height: 100vh;
        overflow: hidden;
    }

    .header {
        background: #7ed957;
        height: 130px;
        width: 100vw;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
    }

    .header h1 {
        color: white;
        font-size: 64px;
        margin: 0;
        font-weight: 700;
    }

    .logo-img {
        position: absolute;
        right: 70px;
        top: 18px;
        width: 100px;
        height: 100px;
        object-fit: contain;
    }

    .main-grid {
        height: calc(100vh - 130px);
        width: 100vw;
        box-sizing: border-box;
        display: grid;
        grid-template-columns: 43fr 17fr 18fr 16fr;
        grid-template-rows: 370px 1fr;
        gap: 18px;
        padding: 22px;
        align-items: stretch;
    }

    .panel {
        background: #7ed957;
        border-radius: 40px;
        padding: 18px 20px;
        box-sizing: border-box;
        overflow: hidden;
    }

    .panel h2 {
        color: white;
        margin: 0 0 14px 8px;
        font-size: 26px;
        font-weight: 700;
        line-height: 1.15;
    }

    .stage-panel {
        grid-column: 1;
        grid-row: 1 / span 2;
        height: 100%;
    }

    .main-grid > .panel:nth-of-type(2),
    .main-grid > .panel:nth-of-type(3),
    .main-grid > .panel:nth-of-type(4) {
        height: 370px;
    }

    .console-panel {
        grid-column: 2 / span 3;
        grid-row: 2;
        height: 100%;
    }

    .stage-grid {
        display: grid;
        grid-template-columns: 305px 115px 165px;
        gap: 24px;
        align-items: start;
        height: calc(100% - 55px);
    }

    .stage-panel h2 {
        font-size: 30px;
        margin-bottom: 18px;
    }

    .stage-panel .section-title {
        color: white;
        font-size: 26px;
        font-weight: 700;
        margin: 10px 0 16px 0;
        text-align: center;
    }

    .stage-panel .row {
        display: flex;
        align-items: center;
        margin-bottom: 16px;
    }

    .stage-panel label {
        font-size: 23px;
        font-weight: 700;
        width: 120px;
        flex-shrink: 0;
    }

    .stage-panel input,
    .stage-panel select {
        width: 170px;
        height: 50px;
        border: none;
        outline: none;
        font-size: 21px;
        padding: 0 10px;
        box-sizing: border-box;
        background: #f0f0f0;
    }

    button {
        border: none;
        cursor: pointer;
        font-weight: 700;
        font-family: Arial, sans-serif;
    }

    .stage-panel .move-btn,
    .stage-panel .small-btn,
    .stage-panel .stop-btn,
    .stage-panel .release-btn {
        width: 92px;
        height: 48px;
        margin-bottom: 12px;
        font-size: 17px;
        border: 2px solid black;
        cursor: pointer;
        font-weight: 700;
        font-family: Arial, sans-serif;
    }

    .stage-panel .move-btn,
    .stage-panel .small-btn {
        background: #2b9360;
        color: white;
    }

    .stage-panel .stop-btn {
        background: #ff3131;
        color: white;
    }

    .stage-panel .release-btn {
        background: #9e9e9e;
        color: white;
        font-size: 12px;
        line-height: 1.1;
    }

    .stage-panel .quick-grid {
        display: grid;
        grid-template-columns: 72px 72px;
        gap: 12px 14px;
        justify-content: center;
        margin-top: 8px;
    }

    .stage-panel .quick-grid .small-btn {
        width: 72px;
        height: 46px;
        margin-bottom: 0;
        font-size: 18px;
    }

    .stage-panel .xy-buttons {
        display: grid;
        grid-template-columns: 92px;
        gap: 10px;
        margin-top: 8px;
    }

    .stage-panel .xy-buttons .small-btn {
        width: 92px;
        height: 48px;
        margin-bottom: 0;
        font-size: 17px;
    }

    .stage-panel .position-box {
        color: white;
        font-size: 17px;
        font-weight: 700;
        margin-top: 8px;
        text-align: center;
    }

    .stage-panel .position-box div {
        margin-bottom: 2px;
    }

    .stage-panel .home-btn {
        width: 145px;
        height: 36px;
        margin-top: 4px;
        background: #2b9360;
        color: white;
        border: 2px solid black;
        font-size: 16px;
        font-weight: 700;
    }

    .large-pill {
        border-radius: 40px;
        width: 200px;
        height: 72px;
        margin: 10px auto;
        display: block;
        font-size: 26px;
    }

    .green-pill {
        background: #2b9360;
        color: white;
        border: 2px solid black;
    }

    .white-pill {
        background: white;
        color: black;
        border: 2px solid black;
    }

    .black-pill {
        background: black;
        color: white;
        border: 2px solid black;
    }

    .light-row {
        display: grid;
        grid-template-columns: 90px 80px 80px;
        align-items: center;
        gap: 8px;
        margin: 12px 0;
    }

    .light-label {
        color: white;
        font-size: 22px;
        font-weight: 700;
    }

    .on-btn, .off-btn {
        width: 80px;
        height: 60px;
        font-size: 24px;
        border: 2px solid black;
    }

    .on-btn {
        background: #2b9360;
        color: white;
    }

    .off-btn {
        background: #ff3131;
        color: white;
    }

    .filter-btn {
        background: #2b9360;
        color: white;
        border-radius: 28px;
        width: 170px;
        height: 56px;
        font-size: 24px;
        display: block;
        margin: 12px auto;
        border: 2px solid black;
    }

    #console {
        background: black;
        color: #00ff99;
        width: 100%;
        height: calc(100% - 58px);
        border-radius: 38px;
        padding: 16px 20px;
        font-family: monospace;
        font-size: 15px;
        overflow-y: auto;
        white-space: pre-wrap;
        box-sizing: border-box;
    }
    </style>
</head>

<body>
    <div class="header">
        <h1>TURTLE Interface</h1>
        <img src="/static/turtle_logo.png" class="logo-img">
    </div>

    <div class="main-grid">

        <div class="panel stage-panel">
            <h2>Stage control</h2>

            <div class="stage-grid">
                <div>
                    <div class="section-title">Individual axis</div>

                    <div class="row">
                        <label>Axis:</label>
                        <select id="axis">
                            <option value="x">X axis</option>
                            <option value="y">Y axis</option>
                            <option value="z">Z axis</option>
                        </select>
                    </div>

                    <div class="row">
                        <label>Steps:</label>
                        <input id="steps" type="number" value="1000">
                    </div>

                    <div class="row">
                        <label>Delay us:</label>
                        <input id="delay_us" type="number" value="2000">
                    </div>

                    <div class="row">
                        <label>Power %:</label>
                        <input id="power" type="number" value="80" min="0" max="100">
                    </div>

                    <div style="height: 8px;"></div>

                    <div class="section-title">Multi axis</div>

                    <div class="row">
                        <label>X-steps:</label>
                        <input id="xy_x_steps" type="number" value="1000">
                    </div>

                    <div class="row">
                        <label>Y-steps:</label>
                        <input id="xy_y_steps" type="number" value="1000">
                    </div>

                    <div class="row">
                        <label>Delay us:</label>
                        <input id="xy_delay_us" type="number" value="2000">
                    </div>

                    <div class="row">
                        <label>Power %:</label>
                        <input id="xy_power" type="number" value="70" min="0" max="100">
                    </div>
                </div>

                <div>
                    <div style="height: 58px;"></div>
                    <button class="move-btn" onclick="movePositive()">Move+</button>
                    <button class="move-btn" onclick="moveNegative()">Move-</button>
                    <button class="stop-btn" onclick="stopMotors()">STOP</button>
                    <button class="release-btn" onclick="releaseMotors()">Release<br>motors</button>

                    <div style="height: 92px;"></div>

                    <div class="xy-buttons">
                        <button class="small-btn" onclick="moveXY(1, 1)">X+Y+</button>
                        <button class="small-btn" onclick="moveXY(1, -1)">X+Y-</button>
                        <button class="small-btn" onclick="moveXY(-1, 1)">X-Y+</button>
                        <button class="small-btn" onclick="moveXY(-1, -1)">X-Y-</button>
                    </div>
                </div>

                <div>
                    <div class="section-title">Quick acces</div>
                    <div class="quick-grid">
                        <button class="small-btn" onclick="quickMove('x', 1)">X+</button>
                        <button class="small-btn" onclick="quickMove('x', -1)">X-</button>
                        <button class="small-btn" onclick="quickMove('y', 1)">Y+</button>
                        <button class="small-btn" onclick="quickMove('y', -1)">Y-</button>
                        <button class="small-btn" onclick="quickMove('z', 1)">Z+</button>
                        <button class="small-btn" onclick="quickMove('z', -1)">Z-</button>
                    </div>

                    <div style="height: 42px;"></div>

                    <div class="section-title">Hold to move</div>
                    <div class="quick-grid">
                        <button class="small-btn jog-btn"
                            onmousedown="startJog('x', 1)"
                            onmouseup="stopJog()"
                            onmouseleave="stopJog()"
                            ontouchstart="startJog('x', 1); event.preventDefault();"
                            ontouchend="stopJog()">X+</button>

                        <button class="small-btn jog-btn"
                            onmousedown="startJog('x', -1)"
                            onmouseup="stopJog()"
                            onmouseleave="stopJog()"
                            ontouchstart="startJog('x', -1); event.preventDefault();"
                            ontouchend="stopJog()">X-</button>

                        <button class="small-btn jog-btn"
                            onmousedown="startJog('y', 1)"
                            onmouseup="stopJog()"
                            onmouseleave="stopJog()"
                            ontouchstart="startJog('y', 1); event.preventDefault();"
                            ontouchend="stopJog()">Y+</button>

                        <button class="small-btn jog-btn"
                            onmousedown="startJog('y', -1)"
                            onmouseup="stopJog()"
                            onmouseleave="stopJog()"
                            ontouchstart="startJog('y', -1); event.preventDefault();"
                            ontouchend="stopJog()">Y-</button>

                        <button class="small-btn jog-btn"
                            onmousedown="startJog('z', 1)"
                            onmouseup="stopJog()"
                            onmouseleave="stopJog()"
                            ontouchstart="startJog('z', 1); event.preventDefault();"
                            ontouchend="stopJog()">Z+</button>

                        <button class="small-btn jog-btn"
                            onmousedown="startJog('z', -1)"
                            onmouseup="stopJog()"
                            onmouseleave="stopJog()"
                            ontouchstart="startJog('z', -1); event.preventDefault();"
                            ontouchend="stopJog()">Z-</button>
                    </div>
	<div style="height: 18px;"></div>

        <div class="position-box">
            <div>Position</div>
            <div>X: <span id="pos_x">0.0</span> µm</div>
            <div>Y: <span id="pos_y">0.0</span> µm</div>
            <div>Z: <span id="pos_z">0.0</span> µm</div>
            <button class="home-btn" onclick="homeStage()">  Home</button>
        </div>
                </div>
            </div>
        </div>


        <div class="panel">
            <h2>Brightfield /<br>Darkfield switch</h2>
            <button class="large-pill green-pill" onclick="setServoAngle(90)">Set Servo</button>
            <button class="large-pill white-pill" onclick="setServoAngle(0)">Brightfield</button>
            <button class="large-pill black-pill" onclick="setServoAngle(180)">Darkfield</button>
        </div>

        <div class="panel">
            <h2>Light source<br>control</h2>

            <div class="light-row">
                <div class="light-label">Laser 1</div>
                <button class="on-btn" onclick="setLight('laser1', true)">ON</button>
                <button class="off-btn" onclick="setLight('laser1', false)">OFF</button>
            </div>

            <div class="light-row">
                <div class="light-label">Laser 2</div>
                <button class="on-btn" onclick="setLight('laser2', true)">ON</button>
                <button class="off-btn" onclick="setLight('laser2', false)">OFF</button>
            </div>

            <div class="light-row">
                <div class="light-label">LED</div>
                <button class="on-btn" onclick="setLight('led', true)">ON</button>
                <button class="off-btn" onclick="setLight('led', false)">OFF</button>
            </div>
        </div>

        <div class="panel">
            <h2 style="text-align:center;">Filter array</h2>
            <button class="filter-btn" onclick="goToFilter(1)">Filter 1</button>
            <button class="filter-btn" onclick="goToFilter(2)">Filter 2</button>
            <button class="filter-btn" onclick="goToFilter(3)">Filter 3</button>
            <button class="filter-btn" onclick="goToFilter(4)">Filter 4</button>
        </div>

        <div class="panel console-panel">
            <h2>Console</h2>
            <div id="console"></div>
        </div>

    </div>

<script>
function log(message) {
    const consoleBox = document.getElementById("console");
    consoleBox.textContent += message + "\\n";
    consoleBox.scrollTop = consoleBox.scrollHeight;
}

async function postJSON(url, data) {
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });

    const result = await response.json();
    log(JSON.stringify(result));
    return result;
}

let jogActive = false;

function startJog(axis, direction) {
    if (jogActive) {
        return;
    }

    jogActive = true;

    const delay_us = parseInt(document.getElementById("delay_us").value);
    const power = parseInt(document.getElementById("power").value);

    postJSON("/api/jog", {
        axis: axis,
        direction: direction,
        delay_us: delay_us,
        power: power
    });
}

function stopJog() {
    if (!jogActive) {
        return;
    }

    jogActive = false;
    postJSON("/api/stop", {});
}

async function updatePosition() {
    try {
        const response = await fetch("/api/state");
        const result = await response.json();

        const UM_PER_STEP = 2 * 1000 / 4096;

        if (result.position) {
            document.getElementById("pos_x").innerText = (result.position.x * UM_PER_STEP).toFixed(1);
            document.getElementById("pos_y").innerText = (result.position.y * UM_PER_STEP).toFixed(1);
            document.getElementById("pos_z").innerText = (result.position.z * UM_PER_STEP).toFixed(1);
        }
    } catch (error) {
        console.log(error);
    }
}

function homeStage() {
    postJSON("/api/home", {
        delay_us: parseInt(document.getElementById("delay_us").value),
        power: parseInt(document.getElementById("power").value)
    });
}

setInterval(updatePosition, 1000);

function getStepperSettings() {
    return {
        axis: document.getElementById("axis").value,
        steps: parseInt(document.getElementById("steps").value),
        delay_us: parseInt(document.getElementById("delay_us").value),
        power: parseInt(document.getElementById("power").value)
    };
}

function movePositive() {
    let settings = getStepperSettings();
    moveStepper(settings.axis, settings.steps, settings.delay_us, settings.power);
}

function moveNegative() {
    let settings = getStepperSettings();
    moveStepper(settings.axis, -settings.steps, settings.delay_us, settings.power);
}

function quickMove(axis, direction) {
    let settings = getStepperSettings();
    moveStepper(axis, direction * settings.steps, settings.delay_us, settings.power);
}

function moveStepper(axis, steps, delay_us, power) {
    postJSON("/api/stepper", {
        axis: axis,
        steps: steps,
        delay_us: delay_us,
        power: power
    });
}

function moveXY(xDirection, yDirection) {
    const xSteps = parseInt(document.getElementById("xy_x_steps").value);
    const ySteps = parseInt(document.getElementById("xy_y_steps").value);
    const delay_us = parseInt(document.getElementById("xy_delay_us").value);
    const power = parseInt(document.getElementById("xy_power").value);

    postJSON("/api/move_xy", {
        x_steps: xDirection * xSteps,
        y_steps: yDirection * ySteps,
        delay_us: delay_us,
        power: power
    });
}

function stopMotors() {
    postJSON("/api/stop", {});
}

function releaseMotors() {
    postJSON("/api/release", {});
}

function setServoAngle(angle) {
    postJSON("/api/servo", {
        angle: angle
    });
}

function setLight(light, state) {
    postJSON("/api/light", {
        light: light,
        state: state
    });
}

function goToFilter(filterNumber) {
    postJSON("/api/filter", {
        filter: filterNumber,
        delay_us: 5000
    });
}

function takePicture(filename, outputType) {
    postJSON("/api/picture", {
        filename: filename,
        output_type: outputType
    });
}
</script>

</body>
</html>
"""


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

@app.route("/api/picture", methods=["POST"])
def api_picture():
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
