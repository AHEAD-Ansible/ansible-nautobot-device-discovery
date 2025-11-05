# Ansible Role: Nautobot Discovery

## Description

This role integrates with Nautobot's API to discover and manage network devices. It processes device facts to create or update entities such as manufacturers, platforms, device roles, device types, tenants, software versions, locations, racks, tags, devices, interfaces, IP addresses, prefixes, VLANs, and VRFs. It supports bulk operations with dynamic chunking for URL and payload safety, using pure Ansible plugins for efficiency.

## Requirements

- Ansible 2.10+
- Access to a Nautobot instance (v2.0+ recommended)
- Python libraries: `requests` (via `ansible.builtin.uri`)
- No external dependencies; uses built-in Nautobot API endpoints

## Role Variables

| Variable | Description | Type | Required | Default |
|----------|-------------|------|----------|---------|
| `nautobot_url` | Nautobot API base URL (e.g., `https://nautobot.example.com`) | string | Yes | - |
| `nautobot_token` | Nautobot API token for authentication | string | Yes | - |
| `device_facts` | List of device dictionaries with facts (e.g., name, serial_number, role, interfaces) | list[dict] | Yes | - |
| `nautobot_namespace` | Default namespace for IPAM objects | string | No | Value from `endpoints.yml` or task logic |
| `nautobot_status` | Default status for new objects (e.g., "Active") | string | No | "Active" |
| `create_missing_locations` | Create locations if missing | boolean | No | true |
| `create_missing_roles` | Create roles if missing | boolean | No | true |
| `continue_on_error` | Ignore errors and continue | boolean | No | false |
| `nautobot_discovery_retry_attempts` | API request retries | integer | No | 3 |
| `nautobot_validate_certs` | Validate SSL certificates | boolean | No | false |
| `default_location_type` | Default location type (e.g., "Site") | string | No | "Site" |

For device_facts structure, see example below. Custom fields and optional attributes (e.g., tags, custom_fields) are supported per entity.

## Dependencies

None.

## Example Playbook

```yaml
---
- hosts: localhost
  gather_facts: false
  roles:
    - role: nautobot_discovery
      vars:
        nautobot_url: "https://nautobot.example.com"
        nautobot_token: "your-api-token-here"
        device_facts:
          - name: "router1"
            serial_number: "ABC123"
            role: "Router"
            location: "Datacenter1"
            platform: "Cisco IOS"
            manufacturer: "Cisco"
            device_type: "ASR1001"
            interfaces:
              - name: "GigabitEthernet0/0"
                type: "1000base-t"
                enabled: true
                status: "Active"
                ip_addresses:
                  - "192.168.1.1/24"
            primary_ip4: "192.168.1.1/24"
            tags: ["production", "core"]
```

Run with: `ansible-playbook playbook.yml`.

## License

MIT.