# roles/nautobot_discovery/filter_plugins/nautobot_filters.py
import ipaddress

def nautobot_extract_prefixes(device_facts):
    prefixes = []
    for fact in device_facts:
        for intf in fact.get('interfaces', []):
            for ip in intf.get('ip_addresses', []):
                prefix = ip if '/' in ip else f"{ip}/32"
                prefixes.append({'prefix': prefix, 'vrf': intf.get('vrf', 'global')})
    return prefixes

def get_interface_for_ip(device_facts, ip_addr):
    for fact in device_facts:
        for intf in fact.get('interfaces', []):
            for ip in intf.get('ip_addresses', []):
                if ip == ip_addr or f"{ip}/32" == ip_addr:
                    return {'device_name': fact['name'], 'name': intf['name'], 'vrf': intf.get('vrf')}
    return None

def dict_diff(existing, planned):
    diff = {}
    for k, v in planned.items():
        if k not in existing or existing[k] != v:
            diff[k] = v
    return diff

def nautobot_is_ip(value):
    """Return True if value is a valid IP (with or without CIDR)."""
    try:
        ipaddress.ip_interface(value)
        return True
    except Exception:
        return False

class FilterModule(object):
    def filters(self):
        return {
            'nautobot_extract_prefixes': nautobot_extract_prefixes,
            'get_interface_for_ip': get_interface_for_ip,
            'dict_diff': dict_diff,
            'nautobot_is_ip': nautobot_is_ip,  # ← NEW
        }