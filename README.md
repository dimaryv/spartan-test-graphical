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

The first screen detects and displays base server characteristics, then lists all discovered test cases with checked checkboxes by default. Use **Select all**, **Deselect all**, and **Run test cases** to control execution.

After starting execution, the app opens a fullscreen run view split vertically:

- left side: live text logs from test case execution;
- right side: all test cases in order with `PENDING`, `RUNNING`, `PASSED`, `FAILED`, or `SKIPPED` status.

Press `Esc` to leave fullscreen mode.

## Test case format

Each test case is a separate folder under `test_cases/` and must contain:

- `metadata.json` with `name`, optional `description`, and optional `command`;
- `run.py`, the default executable script if `command` is omitted.

Example `metadata.json`:

```json
{
  "name": "CPU information",
  "description": "Shows processor model and core count",
  "command": ["{python}", "{case_dir}/run.py"]
}
```

The placeholders are replaced at runtime:

- `{python}`: path to the Python interpreter running the GUI;
- `{case_dir}`: absolute path to the test case folder.

A test case passes when its command exits with code `0`; any non-zero exit code marks it as failed.
