import ipaddress
import json
import urllib.parse

# ----------------------------------------------------------------------
# Nautobot Ansible Filter Plugin
# ----------------------------------------------------------------------
# This module provides custom filters for Nautobot discovery in Ansible.
# All functions are pure, stateless, and idempotent where possible.
# Dependencies: ipaddress (stdlib), json (stdlib), urllib (stdlib).
# No external libs — keeps it lightweight and portable.
#
# Usage in Ansible: Copy to filter_plugins/nautobot_filters.py
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Utility Functions
# ----------------------------------------------------------------------
def nautobot_extract_prefixes(device_facts):
    """Extract unique prefixes from device interfaces' IP addresses.

    Args:
        device_facts (list[dict]): List of device dicts with 'interfaces' key.

    Returns:
        list[dict]: Unique {'prefix': '10.0.0.0/24', 'vrf': 'global'}.

    Example:
        >>> nautobot_extract_prefixes([{'interfaces': [{'ip_addresses': ['10.0.0.1/24']}]})
        [{'prefix': '10.0.0.0/24', 'vrf': 'global'}]

    Notes:
        - Handles /32 for host IPs.
        - Defaults VRF to 'global' if missing.
        - Deduplicates via set.
    """
    prefixes = set()
    for fact in device_facts:
        for intf in fact.get('interfaces', []):
            for ip in intf.get('ip_addresses', []):
                prefix = ip if '/' in ip else f"{ip}/32"
                vrf = intf.get('vrf', 'global')
                prefixes.add((prefix, vrf))
    return [{'prefix': p, 'vrf': v} for p, v in sorted(prefixes)]

def get_interface_for_ip(device_facts, ip_addr):
    """Find interface owning a specific IP.

    Args:
        device_facts (list[dict]): Device facts.
        ip_addr (str): IP like '10.0.0.1' or '10.0.0.1/32'.

    Returns:
        dict or None: {'device_name': 'dev1', 'name': 'eth0', 'vrf': 'global'}.

    Notes:
        - Matches exact IP or with /32 appended.
        - Returns first match (assumes no duplicates).
    """
    for fact in device_facts:
        for intf in fact.get('interfaces', []):
            for ip in intf.get('ip_addresses', []):
                if ip == ip_addr or f"{ip}/32" == ip_addr:
                    return {
                        'device_name': fact['name'],
                        'name': intf['name'],
                        'vrf': intf.get('vrf', 'global')
                    }
    return None

def dict_diff(existing, planned):
    """Compute diff for PATCH: fields in planned not matching existing.

    Args:
        existing (dict): Current object.
        planned (dict): Desired state.

    Returns:
        dict: Changed fields only.

    Example:
        >>> dict_diff({'a': 1, 'b': 2}, {'a': 1, 'c': 3})
        {'c': 3}
    """
    return {k: v for k, v in planned.items() if k not in existing or existing[k] != v}

def nautobot_is_ip(value):
    """Validate if value is a valid IP interface.

    Args:
        value (str): IP string.

    Returns:
        bool: True if valid IP/interface.

    Example:
        >>> nautobot_is_ip('10.0.0.1/24')
        True
    """
    try:
        ipaddress.ip_interface(value)
        return True
    except ValueError:
        return False

def smart_dict_diff(existing, planned):
    """Diff with relationship ID comparison.

    Args:
        existing (dict): Current.
        planned (dict): Desired.

    Returns:
        dict: Changed fields, comparing .id for dicts.

    Notes:
        - For relationships like {'id': 'uuid'}, compares IDs.
    """
    diff = {}
    for k, v in planned.items():
        if k not in existing:
            diff[k] = v
            continue
        ex_v = existing[k]
        if isinstance(v, dict) and isinstance(ex_v, dict) and 'id' in v and 'id' in ex_v:
            if v['id'] != ex_v['id']:
                diff[k] = v
        elif ex_v != v:
            diff[k] = v
    return diff

# ----------------------------------------------------------------------
# API Query Builders
# ----------------------------------------------------------------------
def build_filter_param(f, relationships=None, endpoint_path=None, id_filter_fields=None):
    """Build Nautobot API filter param string.

    Args:
        f (dict): {'key': 'name' or ['device', 'name'], 'value': 'val' or 'val1:val2'}.
        relationships (dict, optional): Relationship mappings.
        endpoint_path (str, optional): Unused (legacy).
        id_filter_fields (list, optional): Unused (legacy).

    Returns:
        str: URL-encoded param like 'name=Global' or 'device=dev1&name=eth0'.

    Notes:
        - Handles composite keys with ':' separated values.
        - Extracts .id from dict values.
    """
    key = f['key']
    value = f['value']

    val = value.get('id', value) if isinstance(value, dict) else value

    if isinstance(key, list):
        parts = []
        values = str(value).split(':') if ':' in str(value) else [value]
        for k, v in zip(key, values):
            v_val = v.get('id', v) if isinstance(v, dict) else v
            parts.append(f"{k}={urllib.parse.quote(str(v_val))}")
        return '&'.join(parts)
    else:
        return f"{key}={urllib.parse.quote(str(val))}"

def build_lookup_filters(desired_bodies, unique_keys, relationships):
    """Build lookup filters for Nautobot GET.

    Args:
        desired_bodies (list[dict]): Desired objects.
        unique_keys (list[str]): Keys like ['name'] or ['device.id', 'name'].
        relationships (dict): Relationship mappings.

    Returns:
        list[dict]: [{'key': ['name'], 'value': 'Global'}].

    Notes:
        - Composites use ':' joined values.
        - Extracts .id for relationships.
    """
    result = []
    for body in desired_bodies:
        filter_keys = []
        parts = []
        for raw_key in unique_keys:
            base_key = raw_key.split('.')[0]
            filter_keys.append(base_key)

            val = body
            for part in raw_key.split('.'):
                val = val.get(part) if isinstance(val, dict) else None
                if val is None:
                    break
            if isinstance(val, dict) and 'id' in val:
                val = val['id']
            parts.append(str(val) if val is not None else '')
        result.append({
            'key': filter_keys,
            'value': ':'.join(parts)
        })
    return result

# ----------------------------------------------------------------------
# Object Matching & Classification
# ----------------------------------------------------------------------
def build_existing_map(objects, unique_keys):
    """Index existing objects by unique key(s).

    Args:
        objects (list[dict]): Nautobot query results.
        unique_keys (list[str]): Keys like ['name'] or ['device.id', 'name'].

    Returns:
        dict: { 'key1:key2': obj, ... }

    Notes:
        - Supports dot-notation (e.g., 'device.id').
        - Extracts .id from nested dicts.
        - Handles None as empty string.
    """
    result = {}
    for obj in objects:
        parts = []
        for raw_key in unique_keys:
            val = obj
            for part in raw_key.split('.'):
                val = val.get(part) if isinstance(val, dict) else None
                if val is None:
                    break
            if isinstance(val, dict) and 'id' in val:
                val = val['id']
            parts.append(str(val) if val is not None else '')
        key = ':'.join(parts)
        result[key] = obj
    return result

def classify_upserts(desired_bodies, existing_map, unique_keys):
    """Classify desired bodies into creates/updates.

    Args:
        desired_bodies (list[dict]): Desired state.
        existing_map (dict): From build_existing_map.
        unique_keys (list[str]): Unique keys.

    Returns:
        dict: {'creates': [], 'updates': [{'id': '...', 'changed_field': '...'}]}

    Notes:
        - Updates only include changed fields + 'id'.
        - Uses smart_dict_diff for relationships.
    """
    creates = []
    updates = []
    for body in desired_bodies:
        key_parts = []
        for raw_key in unique_keys:
            val = body
            for part in raw_key.split('.'):
                val = val.get(part) if isinstance(val, dict) else None
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
            diff = smart_dict_diff(existing, body)
            if diff:
                diff['id'] = existing['id']
                updates.append(diff)
    return {"creates": creates, "updates": updates}

def merge_upsert_results(existing, create_results, update_results):
    """Merge existing, created, and updated objects.

    Args:
        existing (list[dict]): Pre-existing objects.
        create_results (list[dict]): From API (with 'json').
        update_results (list[dict]): From API (with 'json').

    Returns:
        list[dict]: Combined list.

    Notes:
        - Flattens chunked results.
    """
    out = existing[:]
    for chunk in create_results:
        out.extend(chunk.get('json', []))
    for chunk in update_results:
        out.extend(chunk.get('json', []))
    return out

# ----------------------------------------------------------------------
# Prefix & IP Builders
# ----------------------------------------------------------------------
def extract_parent_prefixes(ip_addresses):
    """Extract unique parent networks from IPs.

    Args:
        ip_addresses (list[str]): IPs like ['10.0.0.1/24', '10.0.0.2'].

    Returns:
        list[str]: Sorted unique networks like ['10.0.0.0/24'].

    Notes:
        - Adds /32 for hosts.
        - Skips invalid IPs.
    """
    prefixes = set()
    for ip in ip_addresses or []:
        try:
            iface = ipaddress.ip_interface(ip)
            prefixes.add(str(iface.network))
        except ValueError:
            pass
    return sorted(prefixes)

def build_prefix_bodies(prefixes, namespace_id, status, tenant_id=None):
    """Build Nautobot prefix bodies.

    Args:
        prefixes (list[str]): Networks like ['10.0.0.0/24'].
        namespace_id (str): UUID.
        status (str): 'Active'.
        tenant_id (str, optional): UUID.

    Returns:
        list[dict]: API-ready bodies.

    Notes:
        - Optional tenant.
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

def build_ip_upsert_bodies_from_device(device, namespace_id, status, tenant_id=None, vrf_ids=None):
    """Build IP bodies from device interfaces.

    Args:
        device (dict): Device with 'interfaces'.
        namespace_id (str): UUID.
        status (str): 'Active'.
        tenant_id (str, optional): UUID.
        vrf_ids (dict, optional): {vrf_name: id}.

    Returns:
        dict: {'bodies': [dicts], 'ip_to_id': {} }  # ip_to_id filled post-upsert.

    Notes:
        - Unique IPs.
        - Maps VRF if provided.
    """
    vrf_ids = vrf_ids or {}
    tenant = {'tenant': {'id': tenant_id}} if tenant_id else {}

    all_ips = set()
    ip_to_vrf = {}
    for intf in device.get('interfaces', []):
        vrf = intf.get('vrf')
        for ip in intf.get('ip_addresses', []):
            all_ips.add(ip)
            if vrf:
                ip_to_vrf[ip] = vrf

    bodies = []
    for ip in sorted(all_ips):
        body = {
            'address': ip,
            'namespace': {'id': namespace_id},
            'status': status
        }
        body.update(tenant)
        if ip in ip_to_vrf and ip_to_vrf[ip] in vrf_ids:
            body['vrf'] = {'id': vrf_ids[ip_to_vrf[ip]]}
        bodies.append(body)

    return {"bodies": bodies, "ip_to_id": {}}

# ----------------------------------------------------------------------
# VLAN & VRF Builders
# ----------------------------------------------------------------------
def build_vlan_bodies(vlan_names, location_id, status):
    """Build VLAN bodies.

    Args:
        vlan_names (list[str]): Names like ['internal'].
        location_id (str): UUID.
        status (str): 'Active'.

    Returns:
        list[dict]: API bodies with auto VID (1+).

    Notes:
        - Unique names.
        - VID starts from 1.
    """
    unique_names = set(vlan_names)
    return [
        {'name': name, 'vid': idx, 'location': {'id': location_id}, 'status': status}
        for idx, name in enumerate(sorted(unique_names), start=1)
    ]

def build_vrf_bodies(vrf_names, namespace_id):
    """Build VRF bodies.

    Args:
        vrf_names (list[str]): Names like ['0', '1'].
        namespace_id (str): UUID.

    Returns:
        list[dict]: API bodies with RD = name.

    Notes:
        - Unique names.
    """
    unique_names = set(vrf_names)
    return [
        {'name': name, 'rd': name, 'namespace': {'id': namespace_id}}
        for name in sorted(unique_names)
    ]

# ----------------------------------------------------------------------
# Chunking Utilities
# ----------------------------------------------------------------------
def chunk_list(items, chunk_size):
    """Split list into fixed-size chunks.

    Args:
        items (list): Any list.
        chunk_size (int): Max per chunk.

    Returns:
        list[list]: Chunks.

    Example:
        >>> chunk_list([1,2,3,4], 2)
        [[1, 2], [3, 4]]
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

def smart_chunk_for_lookup(filters, max_url_length=1500):
    """Chunk filters by estimated URL length.

    Args:
        filters (list[dict]): From build_lookup_filters.
        max_url_length (int): Max chars (default 1500).

    Returns:
        list[list[dict]]: Chunks.

    Notes:
        - Accounts for encoding overhead.
        - Safe for GET URLs.
    """
    if not filters:
        return []
    chunks = []
    current_chunk = []
    current_length = 0
    for f in filters:
        param = build_filter_param(f)
        est_len = len(param) + 1  # '&'
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

def smart_chunk_for_payload(bodies, max_payload_bytes=1024*1024):
    """Chunk bodies by JSON payload size.

    Args:
        bodies (list[dict]): API bodies.
        max_payload_bytes (int): Max bytes (default 1MB).

    Returns:
        list[list[dict]]: Chunks.

    Notes:
        - Uses json.dumps for accurate sizing.
        - Accounts for array overhead.
    """
    if not bodies:
        return []
    chunks = []
    current_chunk = []
    current_size = 2  # [] overhead
    for body in bodies:
        body_size = len(json.dumps(body).encode('utf-8')) + 1  # , separator
        if current_chunk and current_size + body_size > max_payload_bytes:
            chunks.append(current_chunk)
            current_chunk = [body]
            current_size = body_size + 2
        else:
            current_chunk.append(body)
            current_size += body_size
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def chunk_prefix_bodies(bodies, nautobot_url, max_url_length=1400, base_url_overhead=50):
    """Chunk prefix bodies by GET URL length (for lookup).

    Args:
        bodies (list[dict]): Prefix bodies.
        nautobot_url (str): Base URL.
        max_url_length (int): Max chars.
        base_url_overhead (int): Extra for headers/etc.

    Returns:
        list[list[dict]]: Chunks of bodies.

    Notes:
        - Uses prefix for estimation.
        - Returns bodies, not strings.
    """
    if not bodies:
        return []

    prefixes = [body['prefix'] for body in bodies]
    base_length = len(nautobot_url.rstrip('/')) + len('/api/ipam/prefixes/?') + base_url_overhead

    def item_to_query(p):
        return f"prefix={urllib.parse.quote(p)}"

    chunks = []
    current_chunk = []
    current_length = base_length

    for prefix, body in zip(prefixes, bodies):
        query_part = item_to_query(prefix)
        est_len = len(query_part) + 1  # '&'
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
# Unique Key Resolver
# ----------------------------------------------------------------------
def resolve_unique_keys(endpoint, lookup_key):
    """Resolve unique keys from endpoint config.

    Args:
        endpoint (dict): From endpoints.yml.
        lookup_key (str): Fallback key.

    Returns:
        list[str]: Keys like ['name'] or ['namespace.id', 'rd'].

    Notes:
        - Prefers 'unique_keys' > 'unique_together' > [lookup_key].
        - Handles lists/tuples.
    """
    unique_keys = endpoint.get('unique_keys')
    if isinstance(unique_keys, (list, tuple)) and unique_keys:
        return list(unique_keys)

    unique_together = endpoint.get('unique_together')
    if isinstance(unique_together, (list, tuple)) and unique_together:
        return list(unique_together)

    return [lookup_key]

# ----------------------------------------------------------------------
# ID List Builder
# ----------------------------------------------------------------------
def build_id_list(ids):
    """Build list of {'id': val} for relationships.

    Args:
        ids (list[str]): UUIDs.

    Returns:
        list[dict]: [{'id': 'uuid1'}, ...]

    Example:
        >>> build_id_list(['uuid1', 'uuid2'])
        [{'id': 'uuid1'}, {'id': 'uuid2'}]
    """
    return [{'id': id_val} for id_val in ids]


# ----------------------------------------------------------------------
# Hierarchical Object Builder
# ----------------------------------------------------------------------
def build_hierarchical_bodies(hierarchy, content_type_map=None, id_map_var=None):
    """
    Build API bodies for hierarchical objects (e.g., location_types).

    Args:
        hierarchy (list[dict]): List of objects with:
            - name (required)
            - content_types (list[str], e.g., ['location', 'rack'])
            - parent_name (optional)
            - other fields (optional)
        content_type_map (dict): {'location': 'dcim.location', ...}
        id_map_var (str): Name of fact containing {name: id} map (for parents)

    Returns:
        dict: {
            'root_bodies': [bodies without parent],
            'child_bodies': [bodies with parent.id],
            'id_map': {name: id}  # from root only
        }

    Example:
        >>> build_hierarchical_bodies([
        ...     {'name': 'Site', 'content_types': ['location']},
        ...     {'name': 'Room', 'parent_name': 'Site', 'content_types': ['rack']}
        ... ], {'location': 'dcim.location', 'rack': 'dcim.rack'})
    """
    content_type_map = content_type_map or {}
    id_map = {}

    root_bodies = []
    child_bodies = []

    for obj in hierarchy:
        # Build base body
        body = {k: v for k, v in obj.items() if k not in ('content_types', 'parent_name')}

        # Transform content_types
        ct_list = obj.get('content_types', [])
        body['content_types'] = [
            content_type_map.get(ct, f"dcim.{ct}") for ct in ct_list
        ]

        # Handle parent
        if 'parent_name' in obj:
            parent_id = None
            if id_map_var:
                # In Ansible context: lookup fact
                import ansible.vars
                # This won't work in pure Python — handled in Ansible task
                pass
            else:
                # In pure test: use local id_map
                parent_id = id_map.get(obj['parent_name'])
            if parent_id:
                body['parent'] = {'id': parent_id}
            child_bodies.append(body)
        else:
            root_bodies.append(body)

    return {
        'root_bodies': root_bodies,
        'child_bodies': child_bodies,
        'id_map': id_map  # populated later
    }


# ----------------------------------------------------------------------
# Filter Registration
# ----------------------------------------------------------------------
class FilterModule(object):
    def filters(self):
        """Register all Nautobot filters."""
        return {
            'nautobot_extract_prefixes': nautobot_extract_prefixes,
            'get_interface_for_ip': get_interface_for_ip,
            'dict_diff': dict_diff,
            'nautobot_is_ip': nautobot_is_ip,
            'smart_dict_diff': smart_dict_diff,
            'build_filter_param': build_filter_param,
            'build_lookup_filters': build_lookup_filters,
            'build_existing_map': build_existing_map,
            'classify_upserts': classify_upserts,
            'merge_upsert_results': merge_upsert_results,
            'extract_parent_prefixes': extract_parent_prefixes,
            'build_prefix_bodies': build_prefix_bodies,
            'chunk_list': chunk_list,
            'smart_chunk_for_lookup': smart_chunk_for_lookup,
            'smart_chunk_for_payload': smart_chunk_for_payload,
            'chunk_prefix_bodies': chunk_prefix_bodies,
            'build_ip_upsert_bodies_from_device': build_ip_upsert_bodies_from_device,
            'build_vlan_bodies': build_vlan_bodies,
            'build_vrf_bodies': build_vrf_bodies,
            'build_id_list': build_id_list,
            'resolve_unique_keys': resolve_unique_keys,
            "build_hierarchical_bodies": build_hierarchical_bodies,
        }