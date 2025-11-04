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
    try:
        ipaddress.ip_interface(value)
        return True
    except Exception:
        return False

def build_filter_param(f, relationships, endpoint_path=None, id_filter_fields=None):
    import urllib.parse

    key = f['key']
    value = f['value']
    id_filter_fields = id_filter_fields or []

    # Extract .id from dicts
    val = value.get('id', value) if isinstance(value, dict) else value

    # === COMPOSITE KEY ===
    if isinstance(key, list):
        parts = []
        values = str(value).split(':') if ':' in str(value) else [value]
        for k, v in zip(key, values):
            v_val = v.get('id', v) if isinstance(v, dict) else v
            field = f"{k}_id" if k in id_filter_fields else k
            parts.append(f"{field}={urllib.parse.quote(str(v_val))}")
        return '&'.join(parts)

    # === SINGLE KEY ===
    else:
        field = f"{key}_id" if key in id_filter_fields else key
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