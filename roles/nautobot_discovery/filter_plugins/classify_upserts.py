# roles/nautobot_discovery/filter_plugins/classify_upserts.py
def classify_upserts(desired_bodies, existing_map, unique_keys):
    """Return (creates, updates) lists from desired vs existing."""
    creates, updates = [], []

    for body in desired_bodies:
        # build composite key
        key_parts = []
        for key in unique_keys:
            parts = key.split(".") if isinstance(key, str) else key
            val = body
            for p in parts:
                if isinstance(val, dict) and p in val:
                    val = val[p]
                else:
                    val = None
                    break
            if val is not None:
                key_parts.append(str(val))
        key = ":".join(key_parts)

        if not key or key not in existing_map:
            creates.append(body)
            continue

        # compare non-readonly fields
        existing = existing_map[key]
        readonly = {
            "id", "url", "created", "last_updated", "display", "natural_slug",
            "notes_url", "object_type", "custom_fields"
        }

        desired_clean = {k: v for k, v in body.items() if k not in readonly}
        existing_clean = {k: v for k, v in existing.items() if k not in readonly}

        if desired_clean != existing_clean:
            updates.append({**desired_clean, "id": existing["id"]})

    return {"creates": creates, "updates": updates}


class FilterModule(object):
    def filters(self):
        return {"classify_upserts": classify_upserts}
