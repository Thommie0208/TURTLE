from flask import Flask, request, jsonify, render_template_string, send_from_directory
import serial
import time
import json
import os
import threading
import RPi.GPIO as GPIO
import ImageGrabAndSave
import numpy as np
import Image_Stitcher

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

required_overlap = 0.10 # fraction (10%)
camera_fov: tuple[float, float] = (1.106 * 1000, 1.659 * 1000)  # x, y (micro m)


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
pico_lock = threading.RLock()  # Reentrant lock to handle recursive retries
MAX_RETRIES = 3
RETRY_DELAY = 0.1  # seconds


def connect_pico():
    global pico

    if pico is not None and pico.is_open:
        return pico

    pico = serial.Serial(PICO_PORT, PICO_BAUD, timeout=15)
    time.sleep(2)
    pico.reset_input_buffer()

    return pico


def send_to_pico(command, retry=0):
    """
    Send a command to the Pico and read the response with thread safety and retry logic.
    """
    with pico_lock:
        try:
            ser = connect_pico()
            
            # Clear any stale data in the buffer
            ser.reset_input_buffer()
            
            line = command + "\r\n"
            ser.write(line.encode("utf-8"))
            
            # Give the Pico time to process and respond
            time.sleep(0.05)
            
            response = ser.readline().decode("utf-8", errors="ignore").strip()

            if response:
                return response

            return "No response from Pico"
            
        except serial.SerialException as e:
            # If it's a read error and we haven't exceeded retries, retry
            if retry < MAX_RETRIES and "returned no data" in str(e):
                time.sleep(RETRY_DELAY * (2 ** retry))  # Exponential backoff
                return send_to_pico(command, retry + 1)
            else:
                return f"Serial error: {str(e)}"
        except Exception as e:
            return f"Error communicating with Pico: {str(e)}"

def send_to_pico_no_wait(command):
    """
    Send a command to the Pico without waiting for a response (fire-and-forget).
    """
    with pico_lock:
        try:
            ser = connect_pico()
            
            # Clear any stale data in the buffer
            ser.reset_input_buffer()
            
            line = command + "\r\n"
            ser.write(line.encode("utf-8"))

            return "sent"
        except Exception as e:
            return f"Error sending to Pico: {str(e)}"


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

    response = send_to_pico_no_wait(json.dumps(command))

    if response.startswith("Error"):
        return {
            "ok": False,
            "error": response,
            "previous_filter": previous_filter,
            "target_filter": target_filter,
            "rotations": rotations,
            "steps": steps,
            "sent": command
        }

    current_filter = target_filter # Update the current filter only if the command was sent successfully

    return {
        "ok": True,
        "message": "Filter move started",
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


@app.route("/api/stepper", methods=["POST"]) #Move a set amount of steps
def api_stepper():
    data = request.json # Get the JSON data from the interface postJSON call

    axis = data.get("axis", "x") # Get the axis to move, default to "x" if not provided
    steps = int(data.get("steps", 100)) # Get the number of steps to move, default to 100 if not provided. Convert to int for safety.
    delay_us = int(data.get("delay_us", 1000))
    power = int(data.get("power", 100))

    command = {
        "cmd": "move",
        "axis": axis,
        "steps": steps,
        "delay_us": delay_us,
        "power": power
    }

    response = send_to_pico(json.dumps(command)) # The response is the Reply function in the Pico code

    return jsonify({
        "sent": command,
        "pico_response": response
    }) #This is the response that will be visible in the console of the interface for debugging purposes.


@app.route("/api/jog", methods=["POST"]) #Moving by holding down a button
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


@app.route("/api/move_xy", methods=["POST"]) #Move an amount of steps in x and y to move diagonally
def api_move_xy():
    data = request.json

    x_steps = int(data.get("x_steps", 0))
    y_steps = int(data.get("y_steps", 0))
    delay_us = int(data.get("delay_us", 2000))
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

@app.route("/api/state", methods=["GET"]) # Get the current position of the stage
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

@app.route("/api/home", methods=["POST"]) # Move the stage to the origin (0, 0, 0)
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

@app.route("/api/filter", methods=["POST"]) # Move the filter wheel to a specific filter (1-4)
def api_filter():
    data = request.json

    target_filter = int(data.get("filter", 1))
    delay_us = int(data.get("delay_us", FILTER_DELAY_US))

    result = move_filter_to(target_filter, delay_us)

    return jsonify(result)


@app.route("/api/stop", methods=["POST"]) #Stop the movement of the stage immediately
def api_stop():
    command = {"cmd": "stop"}
    response = send_to_pico(json.dumps(command))

    return jsonify({
        "sent": command,
        "pico_response": response
    })


@app.route("/api/release", methods=["POST"]) #Remove all power from the motors, allowing for manual movement of the stage
def api_release():
    command = {"cmd": "release"}
    response = send_to_pico(json.dumps(command))

    return jsonify({
        "sent": command,
        "pico_response": response
    })


@app.route("/api/servo", methods=["POST"]) #Move the servo to a specific angle (0, 90 or 180)
def api_servo():
    data = request.json
    angle = int(data.get("angle", 90)) # Default to 90 degrees if not provided

    command = {
        "cmd": "servo",
        "angle": angle
    }

    response = send_to_pico(json.dumps(command))

    return jsonify({
        "sent": command,
        "pico_response": response
    })


@app.route("/api/light", methods=["POST"]) #Control the state of the lasers and LED
def api_light():
    data = request.json

    light = data.get("light", "")
    state = bool(data.get("state", False)) # Expecting a boolean value for state (True for ON, False for OFF)

    if light == "laser1":
        pin = LASER_1_GPIO
    elif light == "laser2":
        pin = LASER_2_GPIO
    elif light == "led":
        pin = LED_GPIO
    else:
        return jsonify({"error": "Invalid light source"}), 400

    GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW) # Set the GPIO pin high or low based on the desired state

    return jsonify({
        "light": light,
        "state": "ON" if state else "OFF"
    })

@app.route("/api/livestream", methods=["POST"]) # Capture a single image for the livestream. The frontend will call this every 0.2 seconds to update the livestream image
def api_livestream():
    success = ImageGrabAndSave.capture_single_image(1, "livestream", timeout_ms=200) #Take an image every 0.2s

    return jsonify({
        "success": success,
        "filename": "livestream.jpg"
    })


@app.route("/api/pictures", methods=["POST"]) # Capture a single image with the specified output type and filename
def api_pictures():
    data = request.json

    filename = data.get("filename", "")
    output_type = data.get("output_type", "raw")

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
    

@app.route("/api/stitch", methods=["POST"]) # Capture a set of images based on the provided stitching points and stitch them together using the stitch function from Image_Stitcher.py
def api_stitch():
    data = request.get_json(silent=True) or {}
    data_points: list[dict[str, str]] = data.get("points", []) #Format is list[dict[str, str]], being [timestamp:, x:, y:]
    foldername: str = data.get("foldername", "")
    output_type_list = ["raw", "jpeg", "bmp", "tiff", "png"]
    
    if not isinstance(data_points, list):
        return jsonify({"error": "Invalid stitching points"}), 400
    if len(data_points) < 3:
        return jsonify({"error": "Not enough stitching points"}), 400
    
    # Create the folder if it doesn't exist
    if foldername and not os.path.exists(foldername):
        os.makedirs(foldername, exist_ok=True)
        
    points = []
    for entry in data_points:
        points.append(float(entry['x']))
        points.append(float(entry['y']))
        
    camera_fov_x: float = data.get("camera_fov_x")
    camera_fov_y: float = data.get("camera_fov_y")


    steps, x_tiles, y_tiles = determine_stitch_square(points, (camera_fov_x, camera_fov_y))
    total_tiles = 0 #Counter used for naming the images
    for i in range(len(steps)):
        send_to_pico(json.dumps(steps[i]))
        time.sleep(6) #Approximate time required for the stage to move
        if steps[i]["steps"] < 0: #This is the command that returns the x to the start to start the next y line
            time.sleep(4) #Approximate time required for the stage to move back
            continue
        total_tiles += 1
        path = os.path.join(foldername, f"{total_tiles}")
        ImageGrabAndSave.capture_single_image(0, path)
        time.sleep(2) # Short delay to ensure the image is saved before moving again
    Image_Stitcher.stitch(foldername, (x_tiles, y_tiles), output_type_list[4]) #Default to png
    return jsonify({
        "ok": True,
        "foldername": foldername,
        "points": points,
        "tiles_x": x_tiles,
        "tiles_y": y_tiles,
        "total_images": total_tiles
    })


def determine_stitch_square(points: list[float], camera_fov: tuple[float, float]) -> tuple[list[dict[str, str | int]], int, int]:
    '''
    Determine the number of tiles in x and y direction based on the provided stitching points and the field of view of the camera, 
    and return a list of movement commands to move the stage to capture all the required images for stitching. 
    Args:
        Points (list[float]): List of stitching points.
        Camera_fov (tuple[float, float]): Field of view of the camera in x and y directions.

    Returns:
        Movement commands (tuple[list[dict[str, str | int]], int, int]): List of movement commands, number of tiles in x direction, number of tiles in y direction.
    '''
    steps: list[dict[str, str | int]] = []
    x1, y1, x2, y2, x3, y3 = points
    top_left: tuple[float, float] = (min(x1, x2, x3), max(y1, y2, y3))
    bottom_right: tuple[float, float] = (max(x1, x2, x3), min(y1, y2, y3))
    normalization_xy: tuple[float, float] = (0 - top_left[0], 0 - top_left[1])
    top_left = (top_left[0] + normalization_xy[0], top_left[1] + normalization_xy[1]) # Normalize the coordinates so that the top left is at (0,0)
    bottom_right = ((bottom_right[0] + normalization_xy[0]), -(bottom_right[1] + normalization_xy[1])) # Invert the y coordinates so that they are in the same orientation as the stage movement commands (positive y is downwards)
    
    tiles_in_x = int((bottom_right[0] - top_left[0]) // (camera_fov[0] * (1 - required_overlap))) + 1 # Distance divided by effective field of view, +1 to account for remainder
    tiles_in_y = int((bottom_right[1] - top_left[1]) // (camera_fov[1] * (1 - required_overlap))) + 1
    print(f"tiles in x: {tiles_in_x}, tiles in y: {tiles_in_y}")
    stepsize = 1/2048 * 1000 #micro m
    y = camera_fov[1] * (1 - required_overlap) #Starts at the first tile distance so the end bound can be inclusive 
    x = camera_fov[0] * (1 - required_overlap)
    while y <= bottom_right[1]: # Loop over y to move down after the x loop, which moves right
        steps_in_direction = 0
        if steps: #The first step should not move the stage, so only calculate steps if there are already steps in the list. This is because before the first step is taken, an image needs to be made
            steps_in_direction = int(camera_fov[1]* (1 - required_overlap)/stepsize)
            y += steps_in_direction * stepsize
        steps.append({
        "cmd": "move",
        "axis": "y",
        "steps": steps_in_direction,
        "delay_us": 1000,
        "power": 100})
        steps_in_x = 0
        while x <= bottom_right[0]:
            steps_in_direction = int(camera_fov[0]* (1 - required_overlap)/stepsize)
            x += steps_in_direction * stepsize
            steps.append({
            "cmd": "move",
            "axis": "x",
            "steps": steps_in_direction,
            "delay_us": 1000,
            "power": 100
            })
            steps_in_x += steps_in_direction
        steps.append({
            "cmd": "move",
            "axis": "x",
            "steps": -steps_in_x,
            "delay_us": 1000,
            "power": 100
            }) #Once the x loop is done, move back to the start of the next line by moving x back by the amount of steps taken in x
        steps_in_x = 0
        x = camera_fov[0] * (1 - required_overlap) #Reset x to the first tile distance for the next line
    return steps, tiles_in_x, tiles_in_y

@app.route("/api/stack", methods=["POST"])
def api_stack():
    data = request.get_json(silent=True) or {}

    z_start: float = data.get("zStart", 0.0)
    z_end: float = data.get("zEnd", 0.0)
    z_steps: int = data.get("zSteps", 1)
    foldername: str = data.get("folderName", "")

    if not isinstance(z_start, (int, float)) or not isinstance(z_end, (int, float)):
        return jsonify({"error": "Invalid z-stack parameters"}), 400

    z_list = np.arange(z_start, z_end, z_steps)
    stepsize = 1/2048 * 1000 #micro m
    steps = []
    for z in range(len(z_list)):
        steps_in_direction = int((z_list[z] - z_list[z - 1])/stepsize)
        steps.append({
            "cmd": "move",
            "axis": "z",
            "steps": steps_in_direction,
            "delay_us": 1000,
            "power": 100
            })
        
    sleeptime = (((z_end - z_start)/z_steps) * 45) / 10000 # Based on the measurement of 1 cm taking 45 seconds.
    for z, step in zip(z_list, steps):
        send_to_pico(json.dumps(step))
        time.sleep(sleeptime)
        path = os.path.join(foldername, f"{z:.2f}")
        ImageGrabAndSave.capture_single_image(0, path)
        time.sleep(2)

    return jsonify({
        "ok": True,
        "z_start": z_start,
        "z_end": z_end,
        "z_steps": z_steps
    })

if __name__ == "__main__":
    try:
        connect_pico()
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

    finally:
        try:
            print("Deleting temporary livestream image")
            livestream_path = os.path.join(APP_DIR, "livestream.jpg")
            if os.path.exists(livestream_path):
                os.remove(livestream_path)
                
            print("Returning stage to origin...")
            command = {
                "cmd": "home",
                "delay_us": 1000,
                "power": 100
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
