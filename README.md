# Spartan Test Graphical

A Python/Tkinter graphical runner for unified server test cases on Ubuntu/Linux.

## Installation

### 1. Install system packages

On Ubuntu, install Python, Tkinter bindings, Git, and `lsblk` from `util-linux`:

```bash
sudo apt update
sudo apt install -y python3 python3-tk git util-linux
```

> `python3-tk` is required for the graphical interface. `util-linux` provides `lsblk`, which is used by the sample disk test case.

### 2. Get the project

Clone the repository or copy the project directory to the server:

```bash
git clone <repository-url>
cd spartan-test-graphical
```

If you already have the project folder, just open it:

```bash
cd /path/to/spartan-test-graphical
```

### 3. Optional: make scripts executable

The scripts in this repository are already marked executable, but you can restore the executable bit if files were copied without permissions:

```bash
chmod +x app.py test_cases/*/run.py
```

## Run

Start the application from a graphical Linux session:

```bash
python3 app.py
```

If you connect to the server over SSH, enable X11 forwarding and make sure an X server is available on your workstation:

```bash
ssh -X user@server
cd /path/to/spartan-test-graphical
python3 app.py
```

The application opens fullscreen. The first screen detects and displays base server characteristics, shows the current FRU Asset Tag JSON stub, lets you choose a server configuration, and lets you adjust replaceable component counts. Use **Select all**, **Deselect all**, and **▶ Run test cases** to control the filtered test list.

After starting execution, the app opens a fullscreen run view split vertically:

- left side: live text logs from test case execution with colored highlights for running, passed, failed, skipped, and error messages;
- right side: all test cases in order with color-coded `PENDING`, `RUNNING`, `PASSED`, `FAILED`, or `SKIPPED` status badges and a spinner animation while a test is running.

Press `Esc` to leave fullscreen mode. The sample suite includes a `Sleep 20 seconds` test case so you can see the running animation before the test completes.

## Project structure

The GUI is split into small modules instead of one large file:

- `app.py` starts Tkinter and wires together configuration, Asset Tag, and the selection window.
- `spartan_runner/config_store.py` loads server configuration templates from `configs/server_configs.json`.
- `spartan_runner/asset_tag.py` contains the current `ipmitool fru` Asset Tag stub.
- `spartan_runner/test_cases.py` discovers and filters test cases by selected server configuration.
- `spartan_runner/ui/selection_window.py` implements the fullscreen configuration and test selection screen.
- `spartan_runner/ui/run_window.py` implements the fullscreen execution report with logs, statuses, and spinner animation.

## Server configurations and component counts

Server configuration templates live in `configs/server_configs.json`. The initial template set contains:

- `intel_2s`: 2xCPU Intel;
- `intel_1s`: 1xCPU Intel;
- `amd_2s`: 2xCPU AMD.

Each template defines the phase, Asset Tag config name, and default counts for CPU, SAS disks, NVMe disks, SSD, HDD, USB flash drives, and memory DIMMs. The selected template and edited component counts are persisted to `data/runtime_state.json` at runtime.

## FRU Asset Tag stub

In production, the selected phase/config state will be written through `ipmitool fru` as JSON, for example:

```json
{"phase": 2, "config": "intel_2s"}
```

Because development hardware is not available yet, the app currently writes and reads the same JSON shape from `data/asset_tag_stub.json` and displays it on the first screen.

## Test case format

Each test case is a separate folder under `test_cases/` and must contain:

- `metadata.json` with `name`, optional `description`, optional `configs`, and optional `command`;
- `run.py`, the default executable script if `command` is omitted.

Example `metadata.json`:

```json
{
  "name": "CPU information",
  "description": "Shows processor model and core count",
  "configs": ["all"],
  "command": ["{python}", "{case_dir}/run.py"]
}
```

The placeholders are replaced at runtime:

- `{python}`: path to the Python interpreter running the GUI;
- `{case_dir}`: absolute path to the test case folder.

A test case passes when its command exits with code `0`; any non-zero exit code marks it as failed. Use `"configs": ["all"]` for checks that apply to every server configuration, or list specific configuration ids such as `"intel_2s"` and `"amd_2s"`.
