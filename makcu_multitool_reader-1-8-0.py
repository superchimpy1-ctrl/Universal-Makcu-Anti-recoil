import json
import time
from pynput import mouse
import keyboard

OUTPUT_FILE = "recorded_path.json"
MIN_DISTANCE = 1  # Changed to 1 to capture slow, tiny movements

path_data = []
last_x, last_y = None, None
last_time = None
is_recording = False

# We need to store the starting absolute position
start_pos = {"x": 0, "y": 0}

def on_move(x, y):
    global last_x, last_y, last_time, is_recording, start_pos
    
    if not is_recording:
        return
        
    current_time = time.time()
    
    if last_x is None:
        # First point: Save where we started
        start_pos = {"x": x, "y": y}
        last_x, last_y, last_time = x, y, current_time
        return
        
    dx = x - last_x
    dy = y - last_y
    distance = (dx**2 + dy**2) ** 0.5
    
    if distance >= MIN_DISTANCE:
        dt = current_time - last_time
        path_data.append({"dx": dx, "dy": dy, "dt": round(dt, 4)})
        last_x, last_y = x, y
        last_time = current_time
        print(f"Recording... Points: {len(path_data)}", end="\r")

def toggle_recording(e):
    global is_recording, last_x, last_y, last_time, path_data
    
    if e.name == 'f1' and e.event_type == 'down':
        if not is_recording:
            is_recording = True
            path_data = []
            last_x, last_y = None, None
            last_time = time.time()
            print("\n\n🔴 RECORDING STARTED...")
        else:
            is_recording = False
            print("\n⏹ RECORDING STOPPED. Saving...")
            
            if len(path_data) > 2:
                save_payload = {
                    "start_x": start_pos["x"],
                    "start_y": start_pos["y"],
                    "points": path_data
                }
                with open(OUTPUT_FILE, "w") as f:
                    json.dump(save_payload, f)
                print(f"✅ Saved {len(path_data)} points. Start Pos: ({start_pos['x']}, {start_pos['y']})")
            else:
                print("❌ Not enough data.")
            time.sleep(0.5)

print("Press F1 to START/STOP recording. Press ESC to quit.")
mouse_listener = mouse.Listener(on_move=on_move)
mouse_listener.start()
keyboard.hook(toggle_recording)

try:
    keyboard.wait('esc')
finally:
    mouse_listener.stop()