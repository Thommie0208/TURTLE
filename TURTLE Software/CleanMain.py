from machine import Pin, PWM
import sys
import json
import time
import select

# -------------------------
# Pin settings
# -------------------------

STBY_PIN = 12
SERVO_PIN = 15

TB6612_MOTORS = {
    "x": {"ain1": 2,  "ain2": 1,  "pwma": 0,  "bin1": 3,  "bin2": 4,  "pwmb": 5},
    "y": {"ain1": 8,  "ain2": 7,  "pwma": 6,  "bin1": 9,  "bin2": 10, "pwmb": 11},
    "z": {"ain1": 18, "ain2": 17, "pwma": 16, "bin1": 19, "bin2": 20, "pwmb": 21},
}

ULN2003_MOTORS = {
    "filter": {"in1": 28, "in2": 27, "in3": 26, "in4": 22}
}

# TB6612 uses half-step sequence
HALF_STEP_SEQUENCE = [
    (1, 0, 0, 0),
    (1, 0, 1, 0),
    (0, 0, 1, 0),
    (0, 1, 1, 0),
    (0, 1, 0, 0),
    (0, 1, 0, 1),
    (0, 0, 0, 1),
    (1, 0, 0, 1),
]

# ULN2003 uses full-step sequence
FULL_STEP_SEQUENCE = [
    (1, 0, 0, 1),
    (0, 0, 1, 1),
    (0, 1, 1, 0),
    (1, 1, 0, 0),
]

STAGE_STEPS_PER_ROTATION = 4096

X_MIN = -int(2.5 * STAGE_STEPS_PER_ROTATION)
X_MAX = int(2.5 * STAGE_STEPS_PER_ROTATION)

Y_MIN = -int(2.5 * STAGE_STEPS_PER_ROTATION)
Y_MAX = int(2.5 * STAGE_STEPS_PER_ROTATION)

Z_MIN = -int(2.5 * STAGE_STEPS_PER_ROTATION)
Z_MAX = int(2.5 * STAGE_STEPS_PER_ROTATION)

stage_position = {
    "x": 0,
    "y": 0,
    "z": 0
}
# -------------------------
# Setup
# -------------------------
servo_pwm = PWM(Pin(SERVO_PIN))
servo_pwm.freq(50)
servo_pwm.duty_u16(0)

tb6612_stby = Pin(STBY_PIN, Pin.OUT)
tb6612_stby.value(1)

tb6612_motors = {}
uln2003_motors = {}

for axis, pins in TB6612_MOTORS.items():
    pwma = PWM(Pin(pins["pwma"]))
    pwmb = PWM(Pin(pins["pwmb"]))

    pwma.freq(20000)
    pwmb.freq(20000)

    tb6612_motors[axis] = {
        "ain1": Pin(pins["ain1"], Pin.OUT),
        "ain2": Pin(pins["ain2"], Pin.OUT),
        "bin1": Pin(pins["bin1"], Pin.OUT),
        "bin2": Pin(pins["bin2"], Pin.OUT),
        "pwma": pwma,
        "pwmb": pwmb,
        "index": 0,
    }

for axis, pins in ULN2003_MOTORS.items():
    uln2003_motors[axis] = {
        "in1": Pin(pins["in1"], Pin.OUT),
        "in2": Pin(pins["in2"], Pin.OUT),
        "in3": Pin(pins["in3"], Pin.OUT),
        "in4": Pin(pins["in4"], Pin.OUT),
        "index": 0,
    }

poll = select.poll()
poll.register(sys.stdin, select.POLLIN)

stop_requested = False

# -------------------------
# Helper functions
# -------------------------

def clamp(value, minimum, maximum):
    value = int(value)
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def reply(data):
    print(json.dumps(data))


def process_pending_commands():
    global stop_requested

    while poll.poll(0):
        line = sys.stdin.readline().strip()

        if not line:
            continue

        try:
            data = json.loads(line)
        except Exception:
            continue

        cmd = data.get("cmd")

        if cmd == "stop":
            stop_requested = True
            reply({"ok": True, "cmd": "stop"})
        elif cmd == "state":
            position_reply()
        elif cmd == "release":
            release_all()
            reply({"ok": True, "cmd": "release"})
        else:
            # Ignore other movement commands while a motor action is already active.
            reply({"ok": False, "error": "busy", "cmd": cmd})


def get_limit(axis):
    if axis == "x":
        return X_MIN, X_MAX
    if axis == "y":
        return Y_MIN, Y_MAX
    if axis == "z":
        return Z_MIN, Z_MAX

    return None, None


def limit_steps(axis, requested_steps):
    if axis not in stage_position:
        return requested_steps

    current = stage_position[axis]
    minimum, maximum = get_limit(axis)

    target = current + requested_steps

    if target > maximum:
        return maximum - current

    if target < minimum:
        return minimum - current

    return requested_steps


def position_reply():
    reply({
        "ok": True,
        "position": stage_position,
        "limits": {
            "x": [X_MIN, X_MAX],
            "y": [Y_MIN, Y_MAX],
            "z": [Z_MIN, Z_MAX]
        }
    })

# -------------------------
# TB6612 functions
# -------------------------

def tb6612_set_power(motor, power):
    power = clamp(power, 0, 100)
    duty = int(65535 * power / 100)

    motor["pwma"].duty_u16(duty)
    motor["pwmb"].duty_u16(duty)


def tb6612_apply_step(motor):
    a1, a2, b1, b2 = HALF_STEP_SEQUENCE[motor["index"]]

    motor["ain1"].value(a1)
    motor["ain2"].value(a2)
    motor["bin1"].value(b1)
    motor["bin2"].value(b2)


def tb6612_step(axis, direction):
    motor = tb6612_motors[axis]
    motor["index"] = (motor["index"] + direction) % len(HALF_STEP_SEQUENCE)
    tb6612_apply_step(motor)


def tb6612_release(motor):
    motor["ain1"].value(0)
    motor["ain2"].value(0)
    motor["bin1"].value(0)
    motor["bin2"].value(0)
    motor["pwma"].duty_u16(0)
    motor["pwmb"].duty_u16(0)


def move_tb6612(axis, steps, delay_us, power):
    global stop_requested

    motor = tb6612_motors[axis]

    steps = int(steps)
    steps = limit_steps(axis, steps)
    delay_us = clamp(delay_us, 500, 1000000)
    power = clamp(power, 0, 100)

    direction = 1
    if steps < 0:
        direction = -1

    steps = abs(steps)

    tb6612_stby.value(1)
    tb6612_set_power(motor, power)

    stop_requested = False

    for _ in range(steps):
        if stop_requested:
            break

        tb6612_step(axis, direction)
        time.sleep_us(delay_us)
        process_pending_commands()

    tb6612_release(motor)

    stage_position[axis] += direction * steps

    reply({
        "ok": True,
        "axis": axis,
        "position": stage_position
    })

def jog_tb6612(axis, direction, delay_us, power):
    global stop_requested

    motor = tb6612_motors[axis]

    direction = int(direction)
    delay_us = clamp(delay_us, 500, 1000000)
    power = clamp(power, 0, 100)

    tb6612_stby.value(1)
    tb6612_set_power(motor, power)

    stop_requested = False

    while not stop_requested:
        if axis in stage_position:
            next_position = stage_position[axis] + direction
            minimum, maximum = get_limit(axis)

            if next_position < minimum or next_position > maximum:
                break

            stage_position[axis] = next_position

        tb6612_step(axis, direction)
        time.sleep_us(delay_us)
        process_pending_commands()

    tb6612_release(motor)
    reply({"ok": True})

def move_xy(x_steps, y_steps, delay_us, power):
    global stop_requested

    x_steps = int(x_steps)
    y_steps = int(y_steps)
    x_steps = limit_steps("x", x_steps)
    y_steps = limit_steps("y", y_steps)

    delay_us = clamp(delay_us, 500, 1000000)
    power = clamp(power, 0, 100)

    x_direction = 1
    y_direction = 1

    if x_steps < 0:
        x_direction = -1

    if y_steps < 0:
        y_direction = -1

    x_steps = abs(x_steps)
    y_steps = abs(y_steps)

    total_steps = max(x_steps, y_steps)

    if total_steps == 0:
        reply({"ok": True})
        return

    tb6612_stby.value(1)

    if x_steps > 0:
        tb6612_set_power(tb6612_motors["x"], power)

    if y_steps > 0:
        tb6612_set_power(tb6612_motors["y"], power)

    stop_requested = False

    x_error = 0
    y_error = 0

    for _ in range(total_steps):
        if stop_requested:
            break

        x_error += x_steps
        y_error += y_steps

        if x_error >= total_steps:
            tb6612_step("x", x_direction)
            x_error -= total_steps

        if y_error >= total_steps:
            tb6612_step("y", y_direction)
            y_error -= total_steps

        time.sleep_us(delay_us)
        process_pending_commands()

    tb6612_release(tb6612_motors["x"])
    tb6612_release(tb6612_motors["y"])

    stage_position["x"] += x_direction * x_steps
    stage_position["y"] += y_direction * y_steps

    reply({
        "ok": True,
        "position": stage_position
    })


def home_stage(delay_us=2000, power=80):
    if stage_position["x"] != 0:
        move_tb6612("x", -stage_position["x"], delay_us, power)

    if stage_position["y"] != 0:
        move_tb6612("y", -stage_position["y"], delay_us, power)

    if stage_position["z"] != 0:
        move_tb6612("z", -stage_position["z"], delay_us, power)

    reply({
        "ok": True,
        "message": "stage returned to origin",
        "position": stage_position
    })


# -------------------------
# ULN2003 functions
# -------------------------

def uln2003_apply_step(motor):
    s1, s2, s3, s4 = FULL_STEP_SEQUENCE[motor["index"]]

    motor["in1"].value(s1)
    motor["in2"].value(s2)
    motor["in3"].value(s3)
    motor["in4"].value(s4)


def uln2003_release(motor):
    motor["in1"].value(0)
    motor["in2"].value(0)
    motor["in3"].value(0)
    motor["in4"].value(0)


def move_uln2003(axis, steps, delay_us):
    global stop_requested

    motor = uln2003_motors[axis]

    steps = int(steps)
    delay_us = clamp(delay_us, 1000, 1000000)

    direction = 1
    if steps < 0:
        direction = -1

    steps = abs(steps)

    stop_requested = False

    for _ in range(steps):
        if stop_requested:
            break

        motor["index"] = (motor["index"] + direction) % len(FULL_STEP_SEQUENCE)
        uln2003_apply_step(motor)

        time.sleep_us(delay_us)
        process_pending_commands()

    uln2003_release(motor)

    reply({"ok": True})

def set_servo_angle(angle):
    angle = int(angle)

    if angle < 0:
        angle = 0
    if angle > 180:
        angle = 180

    # 50 Hz servo signal:
    # 0 degrees   ≈ 0.5 ms pulse
    # 180 degrees ≈ 2.5 ms pulse
    pulse_us = 500 + (angle / 180) * 2000

    # 20 ms period at 50 Hz
    duty = int((pulse_us / 20000) * 65535)

    servo_pwm.duty_u16(duty)
    time.sleep(0.3)
    servo_pwm.duty_u16(0)

    reply({"ok": True})
# -------------------------
# Command handling
# -------------------------

def release_all():
    for motor in tb6612_motors.values():
        tb6612_release(motor)

    for motor in uln2003_motors.values():
        uln2003_release(motor)


def handle_command(line):
    global stop_requested

    data = json.loads(line)
    cmd = data.get("cmd")

    if cmd == "move":
        axis = data.get("axis", "x")
        steps = data.get("steps", 100)
        delay_us = data.get("delay_us", 2000)
        power = data.get("power", 70)

        if axis in tb6612_motors:
            move_tb6612(axis, steps, delay_us, power)

        elif axis in uln2003_motors:
            move_uln2003(axis, steps, delay_us)

    elif cmd == "jog":
        axis = data.get("axis", "x")
        direction = data.get("direction", 1)
        delay_us = data.get("delay_us", 2000)
        power = data.get("power", 70)

        jog_tb6612(axis, direction, delay_us, power)

    elif cmd == "move_xy":
        move_xy(
            data.get("x_steps", 0),
            data.get("y_steps", 0),
            data.get("delay_us", 3000),
            data.get("power", 70)
        )

    elif cmd == "state":
        position_reply()

    elif cmd == "home":
        home_stage(
            data.get("delay_us", 2000),
            data.get("power", 80)
        )

    elif cmd == "stop":
        stop_requested = True
        release_all()
        reply({"ok": True})

    elif cmd == "release":
        release_all()
        reply({"ok": True})

    elif cmd == "servo":
        set_servo_angle(data.get("angle", 90))
    else:
        reply({"ok": False, "error": "unknown command"})


# -------------------------
# Main loop
# -------------------------

release_all()
reply({"ok": True})

buffer = ""

while True:
    if poll.poll(10):
        char = sys.stdin.read(1)

        if char == "\n" or char == "\r":
            line = buffer.strip()
            buffer = ""

            if line:
                handle_command(line)

        else:
            buffer += char