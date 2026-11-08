"""Local development entry point. Never binds to every interface."""

import ipaddress
import json
import os
import subprocess
import sys

from app import create_app


def interface_ipv4_addresses(interface):
    """Read IPs assigned to an explicitly named local network interface."""
    if sys.platform.startswith("linux"):
        command = ["ip", "-j", "-4", "addr", "show", "dev", interface]
        try:
            output = subprocess.run(command, check=True, capture_output=True, text=True).stdout
            entries = json.loads(output)
        except (OSError, subprocess.CalledProcessError, ValueError) as error:
            raise ValueError("Could not verify the selected Host-only interface") from error
        return {address.get("local") for entry in entries for address in entry.get("addr_info", [])}
    if os.name == "nt":
        command = [
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "Get-NetIPAddress -AddressFamily IPv4 | "
            "Select-Object IPAddress,InterfaceAlias | ConvertTo-Json -Compress",
        ]
        try:
            output = subprocess.run(command, check=True, capture_output=True, text=True).stdout
            entries = json.loads(output)
        except (OSError, subprocess.CalledProcessError, ValueError) as error:
            raise ValueError("Could not verify the selected Host-only interface") from error
        if isinstance(entries, dict):
            entries = [entries]
        return {entry.get("IPAddress") for entry in entries
                if entry.get("InterfaceAlias") == interface}
    raise ValueError("Host-only interface verification is unsupported on this operating system")


def selected_host():
    address = os.environ.get("CAMPUSSECURE_HOST_ONLY_IP")
    enabled = os.environ.get("CAMPUSSECURE_ENABLE_HOST_ONLY")
    interface = os.environ.get("CAMPUSSECURE_HOST_ONLY_INTERFACE")
    if not any((address, enabled, interface)):
        return "127.0.0.1"
    if enabled != "1" or not address or not interface:
        raise ValueError("Set Host-only enable, IP, and interface together")
    try:
        ip = ipaddress.ip_address(address)
    except ValueError as error:
        raise ValueError("Host-only IP must be a private IPv4 address") from error
    if (ip.version != 4 or not ip.is_private or ip.is_unspecified or ip.is_loopback
            or ip.is_link_local or ip.is_multicast or ip.is_reserved):
        raise ValueError("Host-only IP must be an explicitly selected private IPv4 address")
    if address not in interface_ipv4_addresses(interface):
        raise ValueError("Host-only IP is not assigned to the selected interface")
    return address


if __name__ == "__main__":
    app = create_app()
    app.run(host=selected_host(), port=5000, debug=False, use_reloader=False)
