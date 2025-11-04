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

def build_filter_param(f, relationships, endpoint_path=None):
    """
    Convert a filter dict into URL-safe param string.
    Special case: VRFs use `namespace=<uuid>`, not `namespace_id=`.
    """
    import urllib.parse

    key = f['key']
    value = f['value']

    # === SPECIAL CASE: VRFs use `namespace` (not `_id`) ===
    no_id_suffix = False
    if endpoint_path == "/ipam/vrfs/":
        if key == "namespace" or (isinstance(key, list) and "namespace" in key):
            no_id_suffix = True

    # Case 1: Composite key
    if isinstance(key, list):
        parts = []
        values = str(value).split(':') if ':' in str(value) else [value]
        for k, v in zip(key, values):
            param = _param_from_key_value(k, v, relationships, no_id_suffix=no_id_suffix)
            parts.append(param)
        return '&'.join(parts)

    # Case 2: Single key
    else:
        return _param_from_key_value(key, value, relationships, no_id_suffix=no_id_suffix)


def _param_from_key_value(k, v, relationships, no_id_suffix=False):
    import urllib.parse

    # Extract .id if dict (for relationship objects)
    val = v.get('id', v) if isinstance(v, dict) else v

    # Apply _id suffix only if:
    # - It's a relationship field
    # - AND we're not suppressing it (e.g. VRF namespace)
    if k in relationships and not no_id_suffix:
        field = f"{k}_id"
    else:
        field = k

    return f"{field}={urllib.parse.quote(str(val))}"
class FilterModule(object):
    def filters(self):
        return {
            'nautobot_extract_prefixes': nautobot_extract_prefixes,
            'get_interface_for_ip': get_interface_for_ip,
            'dict_diff': dict_diff,
            'nautobot_is_ip': nautobot_is_ip,
            'build_filter_param': build_filter_param
        }