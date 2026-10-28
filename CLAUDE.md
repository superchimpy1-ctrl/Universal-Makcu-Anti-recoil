!-- FILE CLAUDE.md --
# CLAUDE.md

This file provides guidance to Claude Code (or any LLM assistant) when working with code in this repository.

## Project Overview
Makcu Multitool is a web-based control panel for the MAKCU hardware mouse passthrough device. It allows the user to control mouse movement in two modes
1. Manual Mode Continuous movement while the Left Mouse Button is held, with adjustable XY strength and timing.
2. Path Player Replays recorded JSON mouse paths with variable speed, scaling, and auto-teleport to the recorded start position.

The backend is built with Flask, and the frontend is a single-page HTMLCSSJS application embedded inside the Python file.

## Architecture
- `makcu_web.py` The main application. Contains the Flask server, Tkinter-free UI, background threading loops for hardware control, and the embedded HTML template.
- `recorder.py` A standalone script that uses `pynput` and `keyboard` to record raw mouse movements to `recorded_path.json`. Global hotkey `F1` startsstops.
- `profiles` Directory where saved manual-mode profiles are stored as JSON files.
- `.json` (root) Recorded path files for the Path Player.

### Hardware Control Threading
- `manual_loop()` Runs constantly. Checks `state[current_mode] == manual`, `enabled`, and `lmb_held`. If true, calls `makcu.move()` with the current strengths and sleeps for `tick_interval`.
- `path_loop()` Runs constantly. Checks `state[current_mode] == path`, `enabled`, `lmb_held`, and that `path_data` is not empty. Iterates through the JSON points, applies `scale_mult`, calls `makcu.move()`, and uses a precise `time.perf_counter()` sleep loop to honor the recorded `dt` divided by the speed multiplier.

### Global State
The `state` dictionary is the single source of truth shared between the Flask API, the UI, and the hardware loops. Never modify hardware state directly from a route; always update `state` and let the loops react.

## Development Guidelines
- Do not rename `makcu_web.py` to `makcu.py`. The `pymakcu` library will import your file instead of itself, causing a circular import crash.
- Keep the frontend monochromeglass themed. The aesthetic is intentionally black (`#050505`), dark grey, and white. Avoid adding bright colors (blues, greens, purples) except for semantic indicators (the greenred status dot, the red delete icon).
- Use `0.0.0.0` for Flask. The app must be accessible from the first PC (the one the mouse is physically connected to), so `host=0.0.0.0` is required. Remind the user to open Windows Firewall port 5000 if they can't connect.
- Threading safety State dictionaries are safe to update in Python due to the GIL for simple readswrites, but do not perform long operations inside the Flask routes.

## Common Tasks

### Adding a new hardware parameter
1. Add the key to the `state` dict with a default value.
2. Add an `input` and `input type=range` to the appropriate tab in the HTML.
3. Add the slider to the `bindControl()` calls at the bottom of the `script` tag.
4. Use `state[new_key]` inside `manual_loop()` or `path_loop()`.

### Adding a new profile setting
1. Update `api_profiles` `POST` handler to include the new key in the `json.dump`.
2. Update the `PUT` handler to read it back into `state`.
3. Update `applyProfile()` in the JS to sync the UI.

### Changing the default port
Change `port=5000` in `app.run()`. Remember to tell users to update their firewall rule and browser URL.