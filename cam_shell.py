#!/usr/bin/env python3
"""cam_shell.py — connect to a Sony A7M3 service-mode shell over USB.

The camera must be attached to WSL (usbipd) and in Mass Storage mode
(054c:0c02) or already in service mode (054c:0336).

PMCA (https://github.com/ma1co/Sony-PMCA-RE) is located via --pmca,
$PMCA_PATH, ./vendor/Sony-PMCA-RE, ../Sony-PMCA-RE, ~/Sony-PMCA-RE
or /opt/Sony-PMCA-RE.
"""
import argparse
import os
import signal
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def find_pmca(arg):
    candidates = []
    if arg:
        candidates.append(arg)
    if os.environ.get("PMCA_PATH"):
        candidates.append(os.environ["PMCA_PATH"])
    candidates += [
        os.path.join(HERE, "vendor", "Sony-PMCA-RE"),
        os.path.join(HERE, os.pardir, "Sony-PMCA-RE"),
        os.path.expanduser("~/Sony-PMCA-RE"),
        "/opt/Sony-PMCA-RE",
    ]
    for path in candidates:
        path = os.path.abspath(path)
        if os.path.isdir(os.path.join(path, "pmca")):
            return path
    raise SystemExit(
        "PMCA not found. Run setup.sh, or set PMCA_PATH to the Sony-PMCA-RE "
        "checkout (the directory that contains the 'pmca' package)."
    )


def connect(wait_seconds=30):
    from pmca.commands.usb import importDriver, getDevice, listDevices
    from pmca.usb.sony import (
        SonyMscExtCmdDevice,
        SonySenserDevice,
        SonySenserAuthDevice,
        SonySenserCamera,
    )

    driver_cm = importDriver("libusb")
    driver = driver_cm.__enter__()

    try:
        device = getDevice(driver)
        if device is None:
            raise SystemExit(
                "no Sony camera found. Check that the camera is in Mass "
                "Storage mode and attached to WSL (usbipd)."
            )

        if isinstance(device, SonyMscExtCmdDevice):
            print("switching to service mode ...", flush=True)
            dev = SonySenserAuthDevice(device.driver)
            dev.start()
            dev.authenticate()
            target = None
            for _ in range(wait_seconds * 2):
                time.sleep(0.5)
                try:
                    devices = list(listDevices(driver, True))
                except Exception:
                    continue
                for d in devices:
                    if isinstance(d, SonySenserDevice):
                        target = d
                        break
                if target is not None:
                    break
            if target is None:
                raise SystemExit(
                    "service mode did not appear. Keep usbipd auto-attach "
                    "running (cam-shell.cmd does this) and try again."
                )
            device = target

        if not isinstance(device, SonySenserDevice):
            raise SystemExit("camera is not a Senser device: %r" % (device,))

        print("authenticating ...", flush=True)
        dev = SonySenserAuthDevice(device.driver)
        dev.start()
        dev.authenticate()
        return driver_cm, dev, SonySenserCamera(device)
    except Exception:
        try:
            driver_cm.__exit__(None, None, None)
        except Exception:
            pass
        raise


def one_shot(cam, command, seconds):
    cam.setTerminalEnable(False)
    cam.setTerminalEnable(True)
    time.sleep(0.5)
    cam.dev.writeTerminal(command.encode() + b"\n")

    out = b""
    end = time.time() + seconds
    while time.time() < end:
        try:
            signal.alarm(1)
            data = cam.dev.readTerminal()
            signal.alarm(0)
            if data:
                out += data
                end = time.time() + 0.5
        except Exception:
            signal.alarm(0)
        time.sleep(0.02)
    cam.setTerminalEnable(False)
    return out.decode("utf-8", "replace")


def raw_shell(cam):
    cam.setTerminalEnable(False)
    cam.setTerminalEnable(True)
    time.sleep(0.5)
    try:
        while True:
            try:
                line = input()
            except (EOFError, KeyboardInterrupt):
                break
            if not line.strip():
                continue
            if line.strip() in ("exit", "quit"):
                break
            cam.dev.writeTerminal(line.encode() + b"\n")
            end = time.time() + 3.0
            while time.time() < end:
                try:
                    data = cam.dev.readTerminal()
                except Exception:
                    data = b""
                if data:
                    os.write(1, data)
                    end = time.time() + 0.5
                else:
                    time.sleep(0.02)
    finally:
        cam.setTerminalEnable(False)


def main():
    ap = argparse.ArgumentParser(description="A7M3 service-mode shell over USB")
    ap.add_argument("--pmca", help="path to the Sony-PMCA-RE checkout")
    ap.add_argument("--wait", type=int, default=30,
                    help="seconds to wait for the service-mode device")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("shell", help="PMCA platform shell (help/shell/push/pull)")
    sub.add_parser("raw", help="line-based camera command loop (no prompt)")

    c = sub.add_parser("cmd", help="run one command on the camera")
    c.add_argument("command")
    c.add_argument("--seconds", type=float, default=6)

    p = sub.add_parser("push", help="upload a file")
    p.add_argument("local")
    p.add_argument("remote")

    p2 = sub.add_parser("pull", help="download a file")
    p2.add_argument("remote")
    p2.add_argument("local")

    args = ap.parse_args()
    sys.path.insert(0, find_pmca(args.pmca))

    from pmca.platform import CameraShell
    from pmca.platform.backend.senser import SenserPlatformBackend

    driver_cm, dev, cam = connect(args.wait)
    try:
        if args.cmd == "shell":
            CameraShell(SenserPlatformBackend(cam)).run()
        elif args.cmd == "raw":
            raw_shell(cam)
        elif args.cmd == "cmd":
            print(one_shot(cam, args.command, args.seconds))
        elif args.cmd == "push":
            with open(args.local, "rb") as f:
                cam.writeFile(args.remote, f.read())
            print("pushed", args.local, "->", args.remote)
        elif args.cmd == "pull":
            with open(args.local, "wb") as f:
                cam.readFile(args.remote, f)
            print("pulled", args.remote, "->", args.local)
    finally:
        try:
            dev.stop()
        except Exception:
            pass
        try:
            driver_cm.__exit__(None, None, None)
        except Exception:
            pass


if __name__ == "__main__":
    main()
