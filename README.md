# Pistorasia

A Python application for controlling SiS-PM (EnerGenie) USB power strips. Pistorasia provides both a graphical user interface (GUI) and command-line interface (CLI) for managing multiple power outlet devices.

## Features

### GUI Mode
- **Multi-device support**: Control multiple USB power strips simultaneously with tabbed interface
- **Visual outlet control**: Toggle outlets on/off with color-coded buttons (green=on, red=off)
- **Custom naming**: Rename both devices and individual outlets for easy identification
- **Device discovery**: Automatic detection and refresh of connected devices
- **Persistent configuration**: Device and outlet names are saved across sessions

### CLI Mode
- **List devices**: View all connected devices and their outlet states
- **Control outlets**: Turn outlets on, off, or toggle their state
- **Flexible selection**: Control outlets by number, custom name, or "all"
- **Multi-outlet operations**: Control multiple outlets simultaneously with comma-separated lists
- **Status queries**: Check the current state of outlets

## Hardware Requirements

Compatible with EnerGenie USB power strips (SiS-PM devices) with the following USB IDs:
- `04b4:fd10`
- `04b4:fd11`
- `04b4:fd12`
- `04b4:fd13`
- `04b4:fd15`

## Installation

### Prerequisites

- Python 3.7 or higher
- USB power strip compatible with SiS-PM protocol

### Install Dependencies

```bash
pip install -r requirements.txt
```

Dependencies include:
- `PySide6` - Qt6 bindings for the GUI
- `pyusb` - USB device communication

### USB Permissions Setup

By default, only root can access USB devices directly. To allow non-root access:

1. Create a udev rules file `/etc/udev/rules.d/60-sispmctl.rules` with the following content:

```
SUBSYSTEM=="usb", ATTR{idVendor}=="04b4", ATTR{idProduct}=="fd10", GROUP="sispmctl", MODE="660"
SUBSYSTEM=="usb", ATTR{idVendor}=="04b4", ATTR{idProduct}=="fd11", GROUP="sispmctl", MODE="660"
SUBSYSTEM=="usb", ATTR{idVendor}=="04b4", ATTR{idProduct}=="fd12", GROUP="sispmctl", MODE="660"
SUBSYSTEM=="usb", ATTR{idVendor}=="04b4", ATTR{idProduct}=="fd13", GROUP="sispmctl", MODE="660"
SUBSYSTEM=="usb", ATTR{idVendor}=="04b4", ATTR{idProduct}=="fd15", GROUP="sispmctl", MODE="660"
```

2. Create the group and add your user:

```bash
sudo groupadd sispmctl
sudo usermod -a -G sispmctl $USER
```

3. Reload udev rules:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

4. Log out and log back in for group changes to take effect

## Usage

### GUI Mode (Default)

Simply run the application without arguments to launch the graphical interface:

```bash
python pistorasia.py
```

The GUI provides:
- Tabs for each connected device
- Toggle buttons for each outlet with visual feedback
- Editable text fields to rename outlets
- Rename device button (pencil icon on tab)
- Refresh button to detect newly connected devices

### CLI Mode

Use the `--cli` flag to access command-line functionality:

#### List all devices and their outlets

```bash
python pistorasia.py --cli --list
```

Example output:
```
[0] Device ID: 01:02:03:04:05, Name: Office Strip
    Outlet 1 (Monitor): ON
    Outlet 2 (Desk Lamp): OFF
    Outlet 3 (Speakers): ON
    Outlet 4 (Outlet 4): OFF
```

#### Turn outlet on

```bash
# By outlet number
python pistorasia.py --cli --outlet 1 --on

# By outlet name
python pistorasia.py --cli --outlet "Monitor" --on

# Multiple outlets
python pistorasia.py --cli --outlet "1,3" --on

# All outlets
python pistorasia.py --cli --outlet all --on
```

#### Turn outlet off

```bash
python pistorasia.py --cli --outlet 1 --off
```

#### Toggle outlet state

```bash
python pistorasia.py --cli --outlet 1 --toggle
```

#### Check outlet status

```bash
python pistorasia.py --cli --outlet 1
```

#### Specify device (when multiple devices connected)

```bash
# By device index
python pistorasia.py --cli --device 0 --outlet 1 --on

# By device ID
python pistorasia.py --cli --device "01:02:03:04:05" --outlet 1 --on

# By device name
python pistorasia.py --cli --device "Office Strip" --outlet 1 --on
```

### CLI Options Reference

- `-l, --list` - List all connected devices and outlet states
- `-d, --device <id>` - Select device by index, ID, or name
- `-o, --outlet <num>` - Select outlet(s) by number, name, comma-separated list, or "all"
- `-1, --on` - Turn selected outlet(s) ON
- `-0, --off` - Turn selected outlet(s) OFF
- `-t, --toggle` - Toggle the state of selected outlet(s)
- `-s, --status` - Get status of selected outlet(s) (default if no action specified)

## Configuration

Configuration files are stored in:
- Linux: `~/.config/pistorasia/devices.json`
- Follows XDG Base Directory specification

The configuration file stores:
- Custom device names
- Custom outlet names for each device
- Device identification by USB ID

Example configuration:
```json
{
    "01:02:03:04:05": {
        "name": "Office Strip",
        "sockets": {
            "1": "Monitor",
            "2": "Desk Lamp",
            "3": "Speakers"
        }
    }
}
```

## License

The sispm module is licensed under a modified BSD license (see `sispm/__init__.py`).

Copyright (c) 2016, Heinrich Schuchardt <xypron.glpk@gmx.de>

## Troubleshooting

### "No SiS-PM devices found"
- Ensure your device is connected and recognized by the system (`lsusb` should show the device)
- Check USB permissions (see USB Permissions Setup above)
- Try running with `sudo` to rule out permission issues

### GUI doesn't start
- Ensure PySide6 is properly installed: `pip install PySide6`
- Check that you have a display server running (X11 or Wayland)

### Device not responding
- Try unplugging and reconnecting the USB device
- Use the "Refresh Devices" button in GUI mode
- Check dmesg for USB errors: `dmesg | tail`

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Credits

- Based on the sispm library for controlling EnerGenie power strips
- GUI built with PySide6 (Qt6 for Python)
