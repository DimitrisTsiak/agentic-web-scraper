import socket
import ipaddress
from urllib.parse import urlparse
from typing import Tuple

ALLOWED_SCHEMES = {"http", "https"}

# Reserved/private IP networks to block (SSRF protection)
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("10.0.0.0/8"),         # Private-use (RFC 1918)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local / Cloud metadata (e.g. AWS 169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),      # Private-use (RFC 1918)
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # Documentation (TEST-NET-1)
    ipaddress.ip_network("192.88.99.0/24"),     # 6to4 Relay Anycast
    ipaddress.ip_network("192.168.0.0/16"),     # Private-use (RFC 1918)
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),    # Documentation (TEST-NET-2)
    ipaddress.ip_network("203.0.113.0/24"),     # Documentation (TEST-NET-3)
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved for future use
    ipaddress.ip_network("::1/128"),            # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 Unique Local Address
    ipaddress.ip_network("fe80::/10"),          # IPv6 Link-local Address
]

def is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP address belongs to any blocked/private network range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in net for net in BLOCKED_IP_NETWORKS)
    except ValueError:
        return True

def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validates a URL for safety against SSRF, bad schemes, and internal access.
    Returns (is_safe, error_reason).
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string."

    try:
        parsed = urlparse(url.strip())
    except Exception as e:
        return False, f"Failed to parse URL: {e}"

    if not parsed.scheme or parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False, f"Disallowed scheme '{parsed.scheme}'. Only http and https are allowed."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL does not contain a valid hostname."

    # Check for localhost explicit hostnames
    if hostname.lower() in {"localhost", "localhost.localdomain", "local"}:
        return False, "Access to localhost hostnames is forbidden."

    # Resolve IP addresses to prevent SSRF
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        resolved_ips = {info[4][0] for info in addr_info}
    except socket.gaierror:
        return False, f"Could not resolve hostname '{hostname}'."

    for ip_str in resolved_ips:
        if is_ip_blocked(ip_str):
            return False, f"Hostname '{hostname}' resolved to blocked/private IP '{ip_str}'."

    return True, "URL is safe."
