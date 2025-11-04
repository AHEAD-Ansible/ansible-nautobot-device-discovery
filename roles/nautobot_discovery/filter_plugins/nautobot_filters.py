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
            # EXTRACT .id FROM DICT
            if isinstance(val, dict) and 'id' in val:
                val = val['id']
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
            # EXTRACT .id IF DICT
            if isinstance(val, dict) and 'id' in val:
                val = val['id']
            parts.append(str(val) if val is not None else '')
        result.append({
            'key': filter_keys,
            'value': ':'.join(parts)
        })
    return result

# ----------------------------------------------------------------------
# 5. extract_parent_prefixes – NEW, RELIABLE, NO JINJA2
# ----------------------------------------------------------------------
def extract_parent_prefixes(ip_addresses):
    """
    Input: list of strings like ['10.0.2.20/24', '10.0.26.122/20', '10.0.100.1/32', '10.0.100.1']
    Output: list of unique parent prefixes like ['10.0.2.0/24', '10.0.26.0/20', '10.0.100.1/32']
    """
    import ipaddress
    prefixes = set()
    for ip in ip_addresses or []:
        try:
            iface = ipaddress.ip_interface(ip)
            prefixes.add(str(iface.network))
        except Exception:
            # Skip invalid IPs
            pass
    return sorted(list(prefixes))

# ----------------------------------------------------------------------
# 6. build_prefix_bodies – NEW, FULLY PLUGIN-BASED
# ----------------------------------------------------------------------
def build_prefix_bodies(prefixes, namespace_id, status, tenant_id=None):
    """
    Input:
      - prefixes: list of strings like ['10.0.2.0/24', '10.0.26.0/20']
      - namespace_id: str (e.g. '8c5f4e9f-...')
      - status: str (e.g. 'Active')
      - tenant_id: str or None
    Output:
      - list of dicts ready for Nautobot API
    """
    bodies = []
    tenant = {'tenant': {'id': tenant_id}} if tenant_id else {}
    for prefix in prefixes or []:
        body = {
            'prefix': prefix,
            'namespace': {'id': namespace_id},
            'status': status
        }
        body.update(tenant)
        bodies.append(body)
    return bodies

# ----------------------------------------------------------------------
# 7. chunk_list – NEW
# ----------------------------------------------------------------------
def chunk_list(items, chunk_size):
    """
    Split list into chunks of size <= chunk_size
    """
    if not items:
        return []
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


# ----------------------------------------------------------------------
# 8. smart_chunk_for_lookup
# ----------------------------------------------------------------------
def smart_chunk_for_lookup(filters, max_url_length=1500):
    if not filters:
        return []
    chunks = []
    current_chunk = []
    current_length = 0
    for f in filters:
        param = f['key'][0] if isinstance(f['key'], list) else f['key']
        value = str(f['value'])
        est_len = len(param) + len(value) + 10
        if current_chunk and current_length + est_len > max_url_length:
            chunks.append(current_chunk)
            current_chunk = [f]
            current_length = est_len
        else:
            current_chunk.append(f)
            current_length += est_len
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

# ----------------------------------------------------------------------
# 9. smart_chunk_for_payload
# ----------------------------------------------------------------------
def smart_chunk_for_payload(bodies, max_payload_bytes=1024*1024):
    import json
    if not bodies:
        return []
    chunks = []
    current_chunk = []
    current_size = 0
    for body in bodies:
        body_size = len(json.dumps(body).encode('utf-8'))
        if current_chunk and current_size + body_size + 10 > max_payload_bytes:
            chunks.append(current_chunk)
            current_chunk = [body]
            current_size = body_size
        else:
            current_chunk.append(body)
            current_size += body_size + 2
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

# ----------------------------------------------------------------------
# 10. resolve_unique_keys – NEW, PURE PYTHON
# ----------------------------------------------------------------------
def resolve_unique_keys(endpoint, lookup_key):
    # endpoint is a dict from YAML
    unique_keys = endpoint.get('unique_keys')
    if isinstance(unique_keys, (list, tuple)) and len(unique_keys) > 0:
        return list(unique_keys)

    unique_together = endpoint.get('unique_together')
    if isinstance(unique_together, (list, tuple)) and len(unique_together) > 0:
        return list(unique_together)

    return [lookup_key]

# ----------------------------------------------------------------------
# 11. chunk_prefix_bodies – FULLY PLUGIN-BASED
# ----------------------------------------------------------------------
def chunk_prefix_bodies(bodies, nautobot_url, max_url_length=1400, base_url_overhead=50):
    """
    Input:
      - bodies: list of prefix dicts
      - nautobot_url: full base URL (e.g. "http://nautobot:8080")
    Output:
      - list of chunks: [[body1, body2], [body3, ...]]
    """
    if not bodies:
        return []

    import urllib.parse

    # Extract prefixes
    prefixes = [body['prefix'] for body in bodies]

    # Build URL-safe query estimator
    base_length = len(nautobot_url.rstrip('/')) + len('/api/ipam/prefixes/?') + base_url_overhead

    def item_to_query(p):
        return f"prefix={urllib.parse.quote(p)}"

    # Chunk by URL length
    chunks = []
    current_chunk = []
    current_length = base_length

    for prefix, body in zip(prefixes, bodies):
        query_part = item_to_query(prefix)
        est_len = len(query_part) + 1  # +1 for '&'

        if current_chunk and current_length + est_len > max_url_length:
            chunks.append(current_chunk)
            current_chunk = [body]
            current_length = base_length + est_len
        else:
            current_chunk.append(body)
            current_length += est_len

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

# ----------------------------------------------------------------------
# 12. build_ip_upsert_bodies_from_device
# ----------------------------------------------------------------------
def build_ip_upsert_bodies_from_device(device, namespace_id, status, tenant_id=None, vrf_ids=None):
    """
    Input:
      - device: full device dict (with .interfaces, .tenant, etc.)
      - namespace_id: str
      - status: str
      - tenant_id: str or None
      - vrf_ids: dict {vrf_name: vrf_id} or None

    Output:
      {
        "bodies": [API-ready dicts],
        "ip_to_id": {}  # to be filled later
      }
    """
    vrf_ids = vrf_ids or {}
    tenant = {'tenant': {'id': tenant_id}} if tenant_id else {}

    # 1. Extract all IPs
    all_ips = []
    ip_to_vrf = {}
    for intf in device.get('interfaces', []):
        ips = intf.get('ip_addresses', [])
        vrf = intf.get('vrf')
        for ip in ips:
            all_ips.append(ip)
            if vrf:
                ip_to_vrf[ip] = vrf

    all_ips = sorted(set(all_ips))  # unique

    # 2. Build bodies
    bodies = []
    for ip in all_ips:
        body = {
            'address': ip,
            'namespace': {'id': namespace_id},
            'status': status
        }
        body.update(tenant)

        # Add VRF if known
        if ip in ip_to_vrf and ip_to_vrf[ip] in vrf_ids:
            body['vrf'] = {'id': vrf_ids[ip_to_vrf[ip]]}

        bodies.append(body)

    return {
        "bodies": bodies,
        "ip_to_id": {}  # caller fills after upsert
    }

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
            'build_lookup_filters': build_lookup_filters,
            'extract_parent_prefixes': extract_parent_prefixes,
            'build_prefix_bodies': build_prefix_bodies,
            'smart_chunk_for_lookup': smart_chunk_for_lookup,
            'smart_chunk_for_payload': smart_chunk_for_payload,
            'resolve_unique_keys': resolve_unique_keys,
            'chunk_prefix_bodies': chunk_prefix_bodies,
            'build_ip_upsert_bodies_from_device': build_ip_upsert_bodies_from_device,
        }