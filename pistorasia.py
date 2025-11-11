#!/usr/bin/env python3
import os
import sys
import argparse
import json
import gc
from dataclasses import dataclass

import usb.core
import sispm

from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QWidget
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QCheckBox
from PySide6.QtWidgets import QTabWidget
from PySide6.QtWidgets import QToolBar
from PySide6.QtWidgets import QInputDialog
from PySide6.QtWidgets import QLineEdit
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QGroupBox
from PySide6.QtWidgets import QLayout
from PySide6.QtWidgets import QTabBar
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt


class App:
    @staticmethod
    def get_config_path():
        config_path = os.path.join(os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "pistorasia")
        os.makedirs(config_path, exist_ok=True)
        return config_path

    @staticmethod
    def get_device_config_path():
        return os.path.join(App.get_config_path(), "devices.json")


@dataclass
class DeviceConfig:
    name: str
    sockets: dict[str, str]  # Mapping from socket number to name


class Device:
    def __init__(self, device):
        self.device_bus = device.bus
        self.device_address = device.address

    @property
    def device(self):
        dev = usb.core.find(bus=self.device_bus, address=self.device_address)
        if dev is None:
            raise Exception("Device not found")
        return dev

    def get_status(self, outlet: int) -> bool:
        return sispm.getstatus(self.device, outlet)

    def set_state(self, outlet: int, state: bool):
        if state:
            sispm.switchon(self.device, outlet)
        else:
            sispm.switchoff(self.device, outlet)

    def get_min_socket(self) -> int:
        return sispm.getminport(self.device)

    def get_max_socket(self) -> int:
        return sispm.getmaxport(self.device)

    def id(self) -> str:
        return sispm.getid(self.device)

    def get_socket_name(self, outlet: int) -> str:
        config_path = App.get_device_config_path()

        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
            if self.id() in config:
                device_config = DeviceConfig(**config[self.id()])
                if str(outlet) in device_config.sockets:
                    return device_config.sockets[str(outlet)]
        return f"Outlet {outlet}"

    def set_socket_name(self, outlet: int, name: str):
        config_path = App.get_device_config_path()
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
        if self.id() in config:
            device_config = DeviceConfig(**config[self.id()])
            device_config.sockets[str(outlet)] = name
            config[self.id()] = device_config.__dict__
        else:
            config[self.id()] = DeviceConfig(name=self.get_name(), sockets={str(outlet): name}).__dict__
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)

    def get_name(self) -> str:
        config_path = App.get_device_config_path()

        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
            if self.id() in config:
                return DeviceConfig(**config[self.id()]).name
        return self.id()

    def set_name(self, name: str):
        config_path = App.get_device_config_path()
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
        if self.id() in config:
            device_config = DeviceConfig(**config[self.id()])
            device_config.name = name
            config[self.id()] = device_config.__dict__
        else:
            config[self.id()] = DeviceConfig(name=name, sockets={}).__dict__
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)


class DeviceManager:
    def __init__(self):
        self.refresh_devices()

    def get_first_device(self) -> Device:
        if not self.devices:
            raise Exception("No SiS-PM devices found")
        return self.devices[0]

    def refresh_devices(self):
        devices = sispm.connect()
        self.devices = [Device(dev) for dev in devices]


class DeviceControlWidget(QWidget):
    def __init__(self, device: Device):
        super().__init__()
        self.device = device
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        min_port = self.device.get_min_socket()
        max_port = self.device.get_max_socket()
        for port in range(min_port, max_port + 1):
            status = self.device.get_status(port)
            port_layout = QHBoxLayout()
            label = QLineEdit(self.device.get_socket_name(port))
            port_layout.addWidget(label)
            label.editingFinished.connect(lambda p=port, l=label: self.edit_socket_name(l, p))
            btn = QPushButton("Power")
            btn.setCheckable(True)
            btn.setChecked(status)
            icon = QIcon.fromTheme("system-shutdown")
            btn.setStyleSheet("background-color: green;" if status else "background-color: red;")
            btn.toggled.connect(lambda checked, p=port: self.device.set_state(p, checked))
            btn.toggled.connect(lambda checked, p=port: print(f"Outlet {p} turned {'ON' if checked else 'OFF'}"))
            btn.toggled.connect(lambda checked, b=btn: b.setStyleSheet("background-color: green;" if checked else "background-color: red;"))
            btn.setIcon(icon)
            btn.setText("")
            port_layout.addWidget(btn)
            layout.addLayout(port_layout)

    def switch_outlet(self, outlet: int, checkbox: QCheckBox):
        self.device.set_state(outlet, checkbox.checkState() == Qt.Checked)
        status = self.device.get_status(outlet)

    def edit_socket_name(self, label: QLineEdit, outlet: int):
        text = label.text()
        ok = True
        if ok and text:
            label.setText(text)
            self.device.set_socket_name(outlet, text)


class ControlWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SiS-PM Control Panel")
        layout = QVBoxLayout()
        toolbar = QToolBar()
        layout.addWidget(toolbar)
        refresh_button = QPushButton("Refresh Devices")
        refresh_button.setIcon(QIcon.fromTheme("view-refresh"))
        refresh_button.clicked.connect(self.refresh_devices)
        toolbar.addWidget(refresh_button)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.device_manager = DeviceManager()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "icon.svg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        for device in self.device_manager.devices:
            device_widget = DeviceControlWidget(device)
            self.tabs.addTab(device_widget, device.get_name())
            # Add a button to rename the device
            rename_button = QPushButton()
            rename_button.setIcon(QIcon.fromTheme("edit-rename"))
            rename_button.clicked.connect(lambda _, d=device: self.rename_device(d))
            rename_button.setToolTip("Rename Device")
            rename_button.setMaximumSize(24, 24)
            rename_button.setFlat(True)
            self.tabs.tabBar().setTabButton(self.tabs.indexOf(device_widget), QTabBar.RightSide, rename_button)
        self.setLayout(layout)

    def rename_device(self, device: Device):
        text, ok = QInputDialog.getText(self, "Rename Device", "Enter new device name:", QLineEdit.Normal, device.get_name())
        if ok and text:
            device.set_name(text)
            # Update tab title
            for i in range(self.tabs.count()):
                # Get device id by widget's device id
                widget = self.tabs.widget(i)
                if widget and widget.device.id() == device.id():
                    self.tabs.setTabText(i, text)
                    break

    def refresh_devices(self):
        self.device_manager.refresh_devices()
        existing_device_ids = set()
        for i in range(self.tabs.count()):
            existing_device_ids.add(self.tabs.tabText(i))
        current_device_ids = set(device.id() for device in self.device_manager.devices)
        current_device_names = set(device.get_name() for device in self.device_manager.devices)
        for i in reversed(range(self.tabs.count())):
            if self.tabs.tabText(i) not in current_device_ids and self.tabs.tabText(i) not in current_device_names:
                print(f"Removing tab for device {self.tabs.tabText(i)}")
                self.tabs.removeTab(i)
        for device in self.device_manager.devices:
            if device.id() not in existing_device_ids and device.get_name() not in existing_device_ids:
                print(f"Adding device {device.id()}")
                device_widget = DeviceControlWidget(device)
                self.tabs.addTab(device_widget, device.get_name())
        gc.collect()


def cli_control():
    parser = argparse.ArgumentParser(description="SiS-PM Command Line Control")
    parser.add_argument("-l", "--list", action="store_true", help="List all connected SiS-PM devices")
    parser.add_argument("-d", "--device", type=str, help="Select device by index (starting from 0)")
    parser.add_argument("-o", "--outlet", type=str, help="Select outlet number")
    parser.add_argument("-1", "--on", action="store_true", help="Turn the selected outlet ON")
    parser.add_argument("-0", "--off", action="store_true", help="Turn the selected outlet OFF")
    parser.add_argument("-s", "--status", action="store_true", help="Get the status of the selected outlet")
    parser.add_argument("-t", "--toggle", action="store_true", help="Toggle the state of the selected outlet")
    parser.add_argument("--cli", action="store_true", help=argparse.SUPPRESS)  # Hidden argument to trigger CLI mode
    args = parser.parse_args()

    device_manager = DeviceManager()
    if args.list:
        for idx, device in enumerate(device_manager.devices):
            print(f"[{idx}] Device ID: {device.id()}, Name: {device.get_name()}")
            for port in range(device.get_min_socket(), device.get_max_socket() + 1):
                status = device.get_status(port)
                print(f"    Outlet {port} ({device.get_socket_name(port)}): {'ON' if status else 'OFF'}")
        return


    # if args.device is None or args.outlet is None:
    #     print("Error: --device and --outlet must be specified for control commands.")
    #     return
    # In case of multiple devices, require --device
    if len(device_manager.devices) > 1 and args.device is None:
        print("Error: Multiple devices found. Please specify --device.")
        return
    if args.device is None:
        args.device = 0  # Default to first device

    # Also device might be specified by id / name
    if args.device is not None:
        try:
            args.device = int(args.device)
        except ValueError:
            # Search by id / name
            for idx, device in enumerate(device_manager.devices):
                if device.id() == args.device or device.get_name() == args.device:
                    args.device = idx
                    break
    if args.device < 0 or args.device >= len(device_manager.devices):
        print("Error: Invalid device index.")
        return

    device = device_manager.devices[args.device]
    if args.outlet is None:
        args.outlet = device.get_min_socket()  # Default to first outlet
        print("Warning: No outlet specified. Defaulting to outlet 0.")


    # Outlet might be specified as number, alias name, comma separated list of the above, or all
    outlets = []
    if isinstance(args.outlet, int):
        outlets = [args.outlet]
    else:
        if args.outlet.lower() == "all":
            outlets = list(range(device.get_min_socket(), device.get_max_socket() + 1))
        else:
            for part in args.outlet.split(","):
                part = part.strip()
                try:
                    outlet_num = int(part)
                    outlets.append(outlet_num)
                except ValueError:
                    # Search by name
                    found = False
                    for port in range(device.get_min_socket(), device.get_max_socket() + 1):
                        if device.get_socket_name(port) == part:
                            outlets.append(port)
                            found = True
                            break
                    if not found:
                        print(f"Warning: Outlet '{part}' not found by number or name.")

    if args.on:
        for outlet in outlets:
            device.set_state(outlet, True)
            print(f"{device.get_name()} [{device.id()}]: {device.get_socket_name(outlet)} [{outlet}] - ON.")
    elif args.off:
        for outlet in outlets:
            device.set_state(outlet, False)
            print(f"{device.get_name()} [{device.id()}]: {device.get_socket_name(outlet)} [{outlet}] - OFF.")
    elif args.toggle:
        for outlet in outlets:
            current_status = device.get_status(outlet)
            device.set_state(outlet, not current_status)
            print(f"{device.get_name()} [{device.id()}]: {device.get_socket_name(outlet)} [{outlet}] - {'ON' if not current_status else 'OFF'}.")
    else:
        for outlet in outlets:
            if outlet < device.get_min_socket() or outlet > device.get_max_socket():
                print(f"Warning: Outlet {outlet} is out of range for device {device.get_name()}.")
                continue
            status = device.get_status(outlet)
            print(f"{device.get_name()} [{device.id()}]: {device.get_socket_name(outlet)} [{outlet}] - {'ON' if status else 'OFF'}.")


def main():
    # If there is --cli in sys.argv, run CLI control
    if "--cli" in sys.argv:
        cli_control()
        return
    app = QApplication([])
    window = ControlWindow()
    window.show()
    app.exec()

if __name__ == "__main__":
    main()
