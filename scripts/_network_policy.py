"""Public-address checks with explicit, bounded Fake-IP proxy compatibility."""
import ipaddress
import os

PROXY_NETWORKS = (ipaddress.ip_network('198.18.0.0/15'), ipaddress.ip_network('fdfe:dcba:9876::/48'))


def address_allowed(address, hostname):
    ip = ipaddress.ip_address(address.split('%', 1)[0])
    if ip.is_global:
        return True
    if os.environ.get('TRAVEL_GUIDE_ALLOW_FAKE_IP') != '1':
        return False
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        # Only DNS results for named hosts may use the known proxy ranges.
        return any(ip in network for network in PROXY_NETWORKS)
    return False
