import ipaddress
import urllib.parse

# ----------------------------------------------------------------------
# Helper utilities (unchanged)
# ----------------------------------------------------------------------
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

# ----------------------------------------------------------------------
# 1. build_filter_param – unchanged (kept for completeness)
# ----------------------------------------------------------------------
def build_filter_param(f, relationships=None, endpoint_path=None, id_filter_fields=None):
    key = f['key']
    value = f['value']

    # Extract .id from dicts
    val = value.get('id', value) if isinstance(value, dict) else value

    # === COMPOSITE KEY ===
    if isinstance(key, list):
        parts = []
        values = str(value).split(':') if ':' in str(value) else [value]
        for k, v in zip(key, values):
            v_val = v.get('id', v) if isinstance(v, dict) else v
            parts.append(f"{k}={urllib.parse.quote(str(v_val))}")
        return '&'.join(parts)

    # === SINGLE KEY ===
    else:
        return f"{key}={urllib.parse.quote(str(val))}"

# ----------------------------------------------------------------------
# 2. NEW build_existing_map – supports dot-notation & relationships
# ----------------------------------------------------------------------
def build_existing_map(objects, unique_keys):
    result = {}
    for obj in objects:
        parts = []
        for raw_key in unique_keys:
            val = obj
            for part in raw_key.split('.'):
                val = val.get(part) if isinstance(val, dict) else None
                if val is None:
                    break
            parts.append(str(val) if val is not None else '')
        result[':'.join(parts)] = obj
    return result

# ----------------------------------------------------------------------
# 3. classify_upserts – uses the new map key format
# ----------------------------------------------------------------------
def classify_upserts(desired_bodies, existing_map, unique_keys):
    """
    Returns:
        {
            "creates": [...],
            "updates": [...]
        }
    """
    creates = []
    updates = []

    for body in desired_bodies:
        # Build the same composite key that build_existing_map uses
        key_parts = []
        for raw_key in unique_keys:
            val = body
            for part in raw_key.split('.'):
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    val = None
                if val is None:
                    break
            if isinstance(val, dict) and 'id' in val:
                val = val['id']
            key_parts.append(str(val) if val is not None else '')
        key = ':'.join(key_parts)

        existing = existing_map.get(key)
        if existing is None:
            creates.append(body)
        else:
            # Only send changed fields (PATCH)
            diff = dict_diff(existing, body)
            if diff:
                diff['id'] = existing['id']   # keep the PK for PATCH
                updates.append(diff)
            # else: nothing to do – already matches

    return {"creates": creates, "updates": updates}

# ----------------------------------------------------------------------
# 4. merge_upsert_results – tiny helper (unchanged, kept for completeness)
# ----------------------------------------------------------------------
def merge_upsert_results(existing, create_results, update_results):
    """
    Existing objects + newly created + patched objects.
    create_results/update_results are lists of dicts returned by api_bulk.yml.
    """
    out = existing[:]
    for chunk in create_results:
        out.extend(chunk.get('json', []))
    for chunk in update_results:
        out.extend(chunk.get('json', []))
    return out

def build_lookup_filters(desired_bodies, unique_keys, relationships):
    result = []
    for body in desired_bodies:
        parts = []
        filter_keys = []
        for raw_key in unique_keys:
            # Use base field name (strip .id)
            base_key = raw_key.split('.')[0]
            filter_keys.append(base_key)

            val = body
            for part in raw_key.split('.'):
                val = val.get(part) if isinstance(val, dict) else None
                if val is None:
                    break
            parts.append(str(val) if val is not None else '')
        result.append({
            'key': filter_keys,
            'value': ':'.join(parts)
        })
    return result

# ----------------------------------------------------------------------
# Filter registration
# ----------------------------------------------------------------------
class FilterModule(object):
    def filters(self):
        return {
            'nautobot_extract_prefixes': nautobot_extract_prefixes,
            'get_interface_for_ip': get_interface_for_ip,
            'dict_diff': dict_diff,
            'nautobot_is_ip': nautobot_is_ip,
            'build_filter_param': build_filter_param,
            'build_existing_map': build_existing_map,
            'classify_upserts': classify_upserts,
            'merge_upsert_results': merge_upsert_results,
            'build_lookup_filters': build_lookup_filters
        }