# roles/nautobot_discovery/filter_plugins/dict_filters.py
# --------------------------------------------------------
# Provides dict_exclude() to safely remove keys from dictionaries.
# This keeps your role compatible without depending on ansible.utils.

def dict_exclude(d, exclude_keys):
    """
    Return a new dict excluding the specified keys.

    Example:
        {{ mydict | dict_exclude(['id', 'url']) }}
    """
    if not isinstance(d, dict):
        # Return as-is if not a dict
        return d

    if not isinstance(exclude_keys, (list, tuple, set)):
        # Allow passing a single string key
        exclude_keys = [exclude_keys]

    return {k: v for k, v in d.items() if k not in exclude_keys}


class FilterModule(object):
    """Custom filters for Nautobot Discovery"""

    def filters(self):
        return {
            "dict_exclude": dict_exclude,
        }
