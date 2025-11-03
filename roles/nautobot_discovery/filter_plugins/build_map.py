from ansible.errors import AnsibleFilterError

def _extract_nested(obj, path):
    """Safely walk nested dict path like ['namespace', 'id']."""
    for p in path:
        if isinstance(obj, dict) and p in obj:
            obj = obj[p]
        else:
            return None
    return obj

def build_existing_map(objects, unique_keys):
    """
    Build a dict mapping composite key strings -> object.
    unique_keys may be list of strings or list of lists for nested paths.
    """
    if not isinstance(objects, list):
        raise AnsibleFilterError("objects must be a list")

    result = {}
    for obj in objects:
        vals = []
        for key in unique_keys:
            # allow "namespace.id" shorthand
            path = key.split(".") if isinstance(key, str) else key
            val = _extract_nested(obj, path)
            if val is not None:
                vals.append(str(val))
        if vals:
            result[":".join(vals)] = obj
    return result

class FilterModule(object):
    def filters(self):
        return {"build_existing_map": build_existing_map}
