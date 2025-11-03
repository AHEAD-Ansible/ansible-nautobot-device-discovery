# `api_upsert.yml` – Universal Bulk Upsert for Nautobot  
**Readme & Usage Guide**

---

## Overview

`api_upsert.yml` is a **universal, DRY, idempotent bulk upsert** task for Nautobot. It:

- Validates input against endpoint schema
- Looks up existing objects in **chunked batches** (URL-safe)
- Compares desired vs. existing (ignoring read-only fields)
- Performs **bulk `POST` (create)** and **bulk `PATCH` (update)**
- Returns a **unified list** of final objects (existing + created + updated)

It uses **custom Ansible filters** and **modular helper tasks** to stay clean and reusable.

---

## Prerequisites

| File | Purpose |
|------|--------|
| `endpoints.yml` | Defines API paths, required/optional fields, relationships, lookup keys |
| `api_upsert.yml` | Main upsert logic |
| `api_bulk.yml` | Handles `POST`/`PATCH` |
| `api_lookup_chunk.yml` | Chunked `GET` lookup |
| Filter plugins: `merge_upsert_results.py`, `build_existing_map.py`, `classify_upsert.py` | Core logic for deduplication, mapping, classification |

> **Place filter plugins in**:  
> `roles/<your_role>/filter_plugins/`  
> or globally in `filter_plugins/`

---

## Required Variables

| Variable | Type | Description |
|--------|------|-----------|
| `endpoint_name` | `string` | Key in `endpoints.yml` (e.g., `"devices"`, `"vrfs"`) |
| `desired_bodies` | `list[dict]` | List of objects **you want to exist** in Nautobot |
| `result_var` | `string` | Name of variable to store final unified result |

---

## Optional Variables

| Variable | Default | Description |
|--------|--------|-----------|
| `override_lookup_key` | `endpoint.lookup_key` | Override lookup field (rarely needed) |
| `extra_lookup_filters` | `{}` | Additional `?key=value` filters for lookup |
| `batch_size` | `50` | Max items per API call |
| `debug_mode` | `false` | Enable verbose debug output |
| `continue_on_error` | `false` | Don't fail on API errors |

---

## How It Works (Step-by-Step)

```yaml
1. Load endpoint definition from endpoints.yml
2. Validate required fields in desired_bodies
3. Build unique key map (from unique_together or lookup_key)
4. Chunked lookup of existing objects via GET
5. Build existing_map using build_existing_map filter
6. Classify creates vs updates using classify_upserts filter
7. Bulk POST creates (chunked)
8. Bulk PATCH updates (chunked)
9. Merge all results → existing + created + updated
10. Return final list in result_var
```

---

## Example: Upsert Devices

```yaml
- name: Upsert core switches
  include_tasks: api_upsert.yml
  vars:
    endpoint_name: devices
    desired_bodies:
      - name: "core-sw01"
        device_type: "Cisco Catalyst 9500"
        role: "Core Switch"
        location: "DC1"
        status: "active"
        platform: "ios"
        serial: "ABC123"
      - name: "core-sw02"
        device_type: "Cisco Catalyst 9500"
        role: "Core Switch"
        location: "DC1"
        status: "active"
        platform: "ios"
        serial: "XYZ789"
    result_var: final_devices
```

> **Result**: `final_devices` = list of all matching devices (existing + new)

---

## Example: Upsert IP Addresses (with namespace)

```yaml
- name: Upsert management IPs
  include_tasks: api_upsert.yml
  vars:
    endpoint_name: ip_addresses
    desired_bodies:
      - address: "10.0.0.1/32"
        namespace: "Global"
        status: "active"
        dns_name: "core-sw01.mgmt"
      - address: "10.0.0.2/32"
        namespace: "Global"
        status: "active"
        dns_name: "core-sw02.mgmt"
    result_var: mgmt_ips
```

> Uses `unique_together: [namespace, address]`

---

## Example: Custom Lookup Filters

```yaml
- name: Upsert only devices in DC1
  include_tasks: api_upsert.yml
  vars:
    endpoint_name: devices
    extra_lookup_filters:
      location: "DC1"
    desired_bodies: [...]
    result_var: dc1_devices
```

---

## Key Filters Explained

| Filter | File | Purpose |
|-------|------|--------|
| `build_existing_map` | `build_existing_map.py` | `{ "key": object }` map from list |
| `classify_upserts` | `classify_upserts.py` | Split into creates/updates |
| `merge_upsert_results` | `merge_upsert_results.py` | Deduplicate + merge final list |

---

## Supported Endpoints (from `endpoints.yml`)

| Endpoint | Lookup Key | Unique Together |
|--------|------------|----------------|
| `namespaces` | `name` | — |
| `manufacturers` | `name` | — |
| `platforms` | `name` | — |
| `device_types` | `model` | — |
| `devices` | `name` | — |
| `interfaces` | `name` | — |
| `ip_addresses` | `address` | `[namespace, address]` |
| `prefixes` | `prefix` | `[namespace, prefix]` |
| `vrfs` | `rd` | — |
| `vlans` | `name` | `[location, vid]` |
| ... | ... | ... |

> Add new endpoints by editing `endpoints.yml`

---

## Best Practices

1. **Always define `result_var`** – you’ll want the final state
2. **Use `name` or natural keys** in `desired_bodies`
3. **Avoid `id`, `url`, `created`** – they’re ignored in comparison
4. **Chunk size ≤ 50** for safety (Nautobot limit ~200, but URLs break earlier)
5. **Use `extra_lookup_filters`** to narrow scope and speed up lookup

---

## Debugging Tips

```yaml
- name: Debug final result
  debug:
    var: final_devices
  when: debug_mode | default(false)
```

Enable globally:
```yaml
vars:
  nautobot_discovery_debug: true
```

---

## Error Handling

- Fails on **missing required fields**
- Retries API calls **3 times**
- Fails early if **query string > 1500 chars**
- Ignores errors if `continue_on_error: true`

---

## Contributing New Endpoints

Edit `endpoints.yml`:

```yaml
my_objects:
  path: /extras/my-objects/
  required_fields: [name]
  optional_fields: [description]
  lookup_key: name
  object_type: extras.myobject
```

Then use:
```yaml
endpoint_name: my_objects
```

---

## Summary

| Feature | Supported |
|-------|-----------|
| Bulk Create | Yes |
| Bulk Update (PATCH) | Yes |
| Idempotent | Yes |
| Chunked & URL-safe | Yes |
| Schema Validation | Yes |
| Relationship-aware | Yes (via `endpoints.yml`) |
| Reusable | Yes One task, any endpoint |

---

**You're now ready to upsert anything in Nautobot safely and efficiently.**

---

> **Pro Tip**: Wrap `api_upsert.yml` in a role task like `upsert_objects.yml` for even cleaner playbooks.

```yaml
# tasks/upsert_objects.yml
- include_tasks: ../api_upsert.yml
  vars:
    endpoint_name: "{{ object_type }}"
    desired_bodies: "{{ objects }}"
    result_var: "{{ object_type }}_final"
```

Then:
```yaml
- include_tasks: upsert_objects.yml
  vars:
    object_type: devices
    objects: "{{ core_switches }}"
```

--- 

**Happy Automating!**