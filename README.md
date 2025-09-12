# Nautobot Discovery Ansible Role

## Overview
The `nautobot_discovery` Ansible role automates the integration of device facts into Nautobot, creating or updating devices, interfaces, IP addresses, prefixes, VLANs, VRFs, static routes, and related metadata. It leverages the `networktocode.nautobot` collection to interact with Nautobot's API, enabling efficient network inventory management and automation.

This role is ideal for network engineers and automation teams looking to synchronize device configurations from sources like Ansible facts gathering or other discovery tools into Nautobot.

## Features
- **Device Management**: Creates or updates devices with details like serial number, model, platform, location, rack, tenant, software version, and primary IP.
- **Interface Management**: Handles interface creation, including type, status, mode (access/tagged), VLAN assignments, VRF assignments, and IP address bindings.
- **IP Address and Prefix Handling**: Parses IPs, manages prefixes (with VRF and tenant support), resolves conflicts by overwriting or using the next available IP, and assigns IPs to interfaces.
- **VLAN Management**: Creates VLANs and assigns them to interfaces as untagged (access) or tagged (trunk).
- **VRF Management**: Creates VRFs, assigns them to devices, interfaces, IPs, and prefixes.
- **Static Route Management**: Creates static routes with destination prefixes, next hops, metrics, VRFs, tenants, and descriptions.
- **Tenant and Software Version Support**: Optionally creates missing tenants and software versions.
- **Conflict Resolution**: Configurable options to overwrite conflicts or allocate next available resources for IPs.
- **Error Tolerance**: Option to continue processing on errors for robust execution.
- **Reusable ID Caching**: Maintains dictionaries for prefix, VRF, VLAN, and tenant IDs to optimize API calls.

## Requirements
- Ansible 2.9 or later.
- `networktocode.nautobot` collection (for Nautobot API interactions).
- `ansible.netcommon` collection (for network utilities).
- Python 3 with the `ipaddress` module (standard library) for IP parsing.
- Access to a Nautobot instance with an API token having read/write permissions for relevant endpoints (e.g., devices, interfaces, IPAM).

No additional package installations are required beyond the collections.

## Installation
Install the required collections using Ansible Galaxy:

```bash
ansible-galaxy collection install networktocode.nautobot
ansible-galaxy collection install ansible.netcommon
```

Clone or download this role into your Ansible roles directory.

## Role Variables
Variables are defined in `defaults/main.yml` and can be overridden in your playbook. Key variables include:

- `create_missing_locations` (bool): Create locations if missing (default: `true`).
- `default_location_type` (str): Default type for new locations (default: `"Datacenter"`).
- `create_missing_racks` (bool): Create racks if missing (default: `true`).
- `create_missing_tenants` (bool): Create tenants if missing (default: `true`).
- `create_missing_software_versions` (bool): Create software versions if missing (default: `true`).
- `continue_on_error` (bool): Continue on errors during device processing (default: `true`).
- `allow_ip_overwrite` (bool): Overwrite conflicting IP assignments (default: `true`).
- `use_next_available_on_conflict` (bool): Use next available IP on conflict (default: `false`).
- `nautobot_namespace` (str): Namespace for IPAM resources (default: `"Global"`).
- `nautobot_status` (str): Default status for created objects (default: `"Active"`).
- `nautobot_validate_certs` (bool): Validate SSL certificates for Nautobot API (default: `false`).

**Required Variables** (must be provided in your playbook):
- `nautobot_url` (str): Nautobot API URL (e.g., `"https://nautobot.example.com"`).
- `nautobot_token` (str): Nautobot API token.
- `device_facts` (list): List of device dictionaries to process (see below).

Internal caching variables (do not override):
- `prefix_ids` (dict): Cached prefix IDs.
- `vrf_ids` (dict): Cached VRF IDs.
- `tenant_ids` (dict): Cached tenant IDs.
- `vlan_ids` (dict): Cached VLAN IDs.

## Device Facts Structure
The `device_facts` variable is a list of dictionaries, each representing a device. Required fields ensure basic device creation, while optional fields enable advanced features like VLANs and routes.

### Required Fields
- `name` (str): Device name (e.g., `"switch01"`).
- `serial_number` (str): Device serial number (e.g., `"SN12345"`).
- `vendor` (str): Manufacturer (e.g., `"Cisco"`).
- `model` (str): Device model (e.g., `"C9300"`).
- `platform` (str): Platform (e.g., `"ios"`).
- `location` (str): Location/site name (e.g., `"Site1"`).
- `device_type` (str): Device role (e.g., `"switch"`).

### Optional Fields
- `tenant` (str): Tenant name (e.g., `"Tenant1"`). Fails if missing and `create_missing_tenants` is `false`.
- `software_version` (str): Software version (e.g., `"17.3.1"`). Fails if missing and `create_missing_software_versions` is `false`.
- `rack` (str): Rack name (e.g., `"Rack1"`). Requires `position` and `face` if specified; fails if missing and `create_missing_racks` is `false`.
- `position` (int): Rack position (e.g., `10`). Required if `rack` is specified.
- `face` (str): Rack face (e.g., `"front"`). Required if `rack` is specified.
- `tags` (list[str]): Tags to apply (e.g., `["core", "prod"]`).
- `custom_fields` (dict): Custom fields (e.g., `{"field1": "value1"}`).
- `asset_tag` (str): Asset tag (e.g., `"ASSET123"`).
- `status` (str): Device status (defaults to `nautobot_status`).
- `comments` (str): Device comments (e.g., `"Core switch"`).
- `primary_ip4` (str): Primary IPv4 address (e.g., `"10.0.0.1/24"`). Must be assigned to an interface.
- `interfaces` (list[dict]): List of interfaces.
  - `name` (str): Interface name (e.g., `"GigabitEthernet0/1"`).
  - `type` (str): Interface type (e.g., `"1000base-t"`).
  - `ip_addresses` (list[str]): IPs (e.g., `["10.0.0.1/24"]`).
  - `vrf` (str): VRF name (e.g., `"VRF1"`).
  - `vlan` (str): Untagged VLAN for access mode (e.g., `"VLAN10"`).
  - `tagged_vlans` (list[str]): Tagged VLANs for trunk mode (e.g., `["VLAN10", "VLAN20"]`).
- `vlans` (list[dict]): List of VLANs.
  - `name` (str): VLAN name (e.g., `"VLAN10"`).
  - `tag` (int): VLAN ID/VID (e.g., `10`).
  - `interfaces` (list[dict]): Interfaces to assign.
    - `name` (str): Interface name (e.g., `"GigabitEthernet0/1"`).
    - `tagged` (str): `"yes"` for tagged (trunk), `"no"` for untagged (access).
- `vrfs` (list[str]): List of VRF names (e.g., `["VRF1", "VRF2"]`).
- `static_routes` (list[dict]): List of static routes.
  - `destination` (str): Destination prefix (e.g., `"10.0.0.0/24"`).
  - `next_hop` (str): Next-hop IP (e.g., `"10.0.0.1"`).
  - `vrf` (str): VRF name (e.g., `"VRF1"`).
  - `tenant` (str): Tenant name (e.g., `"Tenant1"`).
  - `metric` (int): Route metric (default: `1`).
  - `description` (str): Route description (e.g., `"Static route to core"`).

### Example Device Facts
```yaml
device_facts:
  - name: "switch01"
    serial_number: "SN12345"
    vendor: "Cisco"
    model: "C9300"
    platform: "ios"
    location: "Site1"
    device_type: "switch"
    tenant: "Tenant1"                  # Optional
    software_version: "17.3.1"         # Optional
    rack: "Rack1"                      # Optional
    position: 10                       # Optional if rack specified
    face: "front"                      # Optional if rack specified
    tags: ["core", "prod"]             # Optional
    custom_fields:                     # Optional
      field1: "value1"
    asset_tag: "ASSET123"              # Optional
    comments: "Core switch"            # Optional
    interfaces:                        # Optional
      - name: "GigabitEthernet0/1"
        type: "1000base-t"
        vrf: "VRF1"
        vlan: "VLAN10"                 # For access mode
        ip_addresses:
          - "10.0.0.1/24"
      - name: "GigabitEthernet0/2"
        type: "1000base-t"
        tagged_vlans: ["VLAN20", "VLAN30"]  # For trunk mode
    vlans:                             # Optional
      - name: "VLAN10"
        tag: 10
        interfaces:
          - name: "GigabitEthernet0/1"
            tagged: "no"
      - name: "VLAN20"
        tag: 20
        interfaces:
          - name: "GigabitEthernet0/2"
            tagged: "yes"
    vrfs: ["VRF1", "VRF2"]             # Optional
    static_routes:                     # Optional
      - destination: "192.168.0.0/24"
        next_hop: "10.0.0.1"
        vrf: "VRF1"
        tenant: "Tenant1"
        metric: 1
        description: "Route to remote site"
    primary_ip4: "10.0.0.1/24"         # Optional
```

## Usage
Include the role in your playbook and provide the required variables.

### Example Playbook
```yaml
- hosts: localhost
  roles:
    - role: nautobot_discovery
      vars:
        nautobot_url: "https://nautobot.example.com"
        nautobot_token: "your-api-token"
        device_facts: "{{ device_facts }}"  # Define as shown above
```

Run the playbook:
```bash
ansible-playbook your_playbook.yml
```

## Dependencies
- `networktocode.nautobot`
- `ansible.netcommon`

## Directory Structure
- `defaults/main.yml`: Default variables.
- `handlers/main.yml`: Handlers (empty).
- `meta/main.yml`: Role metadata.
- `tasks/`: Core logic.
  - `main.yml`: Validates variables and processes devices.
  - `process_device.yml`: Handles individual devices.
  - `process_interface.yml`: Manages interfaces and IPs.
  - `process_ip.yml`: IP creation and assignment.
  - `process_prefix.yml`: Prefix management.
  - `process_vlan.yml`: VLAN creation and assignment.
  - `process_vrf.yml`: VRF creation and assignment.
  - `process_route.yml`: Static route creation.
  - `process_tenant.yml`: Tenant management.
  - `parse_ip.yml`: IP parsing utility.
  - `lookup_and_normalize.yml`: API lookup utility.
- `tests/test.yml`: Test playbook.
- `vars/main.yml`: Additional variables (empty).

## Notes
- The role uses Python's `ipaddress` for parsing and requires no internet access beyond Nautobot API.
- Conflicts (e.g., IP assignments) are resolved based on `allow_ip_overwrite` and `use_next_available_on_conflict`.
- For static routes, the role uses `ansible.builtin.uri` as no dedicated module exists.
- Debug messages are included for troubleshooting; enable verbose mode (`-vv`) for details.
- Ensure Nautobot has required content types enabled for location types (e.g., devices, racks, VLANs).

## License
MIT

## Author
Brian Nelson