# Nautobot Discovery Ansible Role

## Overview
The `nautobot_discovery` Ansible role automates the process of uploading device facts to a Nautobot instance, ensuring that devices, interfaces, IP addresses, and associated metadata are accurately represented in Nautobot. This role is designed to integrate with the `networktocode.nautobot` collection to interact with Nautobot's API, facilitating network automation tasks.

## Features
- **Device Management**: Creates or updates devices in Nautobot based on provided device facts, including serial number, model, platform, and location.
- **Interface Management**: Manages device interfaces and assigns IP addresses to them.
- **IP Address Handling**: Parses, validates, and assigns IP addresses, handling conflicts by either overwriting or allocating the next available IP.
- **Prefix Management**: Ensures network prefixes exist in Nautobot and associates them with IP addresses.
- **Flexible Configuration**: Supports customizable behavior for creating missing entities (locations, racks, tenants, software versions) and handling IP conflicts.
- **Error Handling**: Configurable to continue on errors, ensuring robust execution in diverse environments.

## Requirements
- Ansible 2.9 or later
- `networktocode.nautobot` collection
- `ansible.netcommon` collection
- Python with `ipaddress` module for IP parsing
- Access to a Nautobot instance with API token

## Role Variables
The role uses several variables defined in `defaults/main.yml` to control its behavior:

- `create_missing_locations`: Create locations if they don't exist (default: `true`).
- `create_missing_racks`: Create racks if they don't exist (default: `true`).
- `create_missing_tenants`: Create tenants if they don't exist (default: `true`).
- `create_missing_software_versions`: Create software versions if they don't exist (default: `true`).
- `continue_on_error`: Continue execution on errors (default: `true`).
- `allow_ip_overwrite`: Overwrite conflicting IP assignments (default: `true`).
- `use_next_available_on_conflict`: Use the next available IP on conflict (default: `false`).
- `nautobot_namespace`: Namespace for IP and prefix lookups (default: `"Global"`).
- `nautobot_status`: Default status for created objects (default: `"Active"`).
- `nautobot_validate_certs`: Validate Nautobot API certificates (default: `false`).
- `prefix_ids`: Dictionary to store prefix IDs (default: `{}`).

**Required Variables**:
- `nautobot_url`: URL of the Nautobot API.
- `nautobot_token`: API token for Nautobot authentication.
- `device_facts`: List of device facts to process (see below for structure).

## Device Facts Structure
The `device_facts` variable is a list of dictionaries, each representing a device to be processed. Below is the structure with required and optional fields:

### Required Fields
- `name`: The name of the device (e.g., `"switch01"`).
- `serial_number`: The device's serial number (e.g., `"SN12345"`).
- `vendor`: The device manufacturer (e.g., `"Cisco"`).
- `model`: The device model (e.g., `"C9300"`).
- `platform`: The device platform (e.g., `"ios"`).
- `location`: The device location/site (e.g., `"Site1"`).
- `device_type`: The device role/type (e.g., `"switch"`).

### Optional Fields
- `tenant`: The tenant associated with the device (e.g., `"Tenant1"`). If not found and `create_missing_tenants` is `false`, the task fails.
- `software_version`: The software version running on the device (e.g., `"17.3.1"`). If not found and `create_missing_software_versions` is `false`, the task fails.
- `rack`: The rack where the device is located (e.g., `"Rack1"`). If specified and not found, requires `create_missing_racks` to be `true` to create it.
- `position`: The rack position (e.g., `10`). Required if `rack` is specified.
- `face`: The rack face (e.g., `"front"`). Required if `rack` is specified.
- `tags`: List of tags to apply to the device (e.g., `["core", "prod"]`). Created if they don't exist.
- `custom_fields`: Dictionary of custom fields for the device (e.g., `{"field1": "value1"}`).
- `asset_tag`: The asset tag for the device (e.g., `"ASSET123"`).
- `status`: The device status (e.g., `"Active"`). Defaults to `nautobot_status` if not provided.
- `comments`: Comments for the device (e.g., `"Core switch for prod"`).
- `interfaces`: List of interfaces on the device. Each interface requires:
  - `name`: Interface name (e.g., `"GigabitEthernet0/1"`).
  - `type`: Interface type (e.g., `"1000base-t"`).
  - `ip_addresses`: List of IP addresses (e.g., `["10.0.0.1/24"]`).
- `primary_ip4`: The primary IPv4 address for the device (e.g., `"10.0.0.1/24"`). Must be assigned to an interface if specified.

### Example Device Facts
```yaml
device_facts:
  - name: "device1"
    serial_number: "SN12345"
    vendor: "Cisco"
    model: "C9300"
    platform: "ios"
    location: "Site1"
    device_type: "switch"
    tenant: "Tenant1"              # Optional
    software_version: "17.3.1"     # Optional
    rack: "Rack1"                  # Optional
    position: 10                   # Optional, required if rack is specified
    face: "front"                  # Optional, required if rack is specified
    tags: ["core", "prod"]         # Optional
    custom_fields:                 # Optional
      field1: "value1"
    asset_tag: "ASSET123"          # Optional
    status: "Active"               # Optional
    comments: "Core switch"        # Optional
    interfaces:                    # Optional
      - name: "GigabitEthernet0/1"
        type: "1000base-t"
        ip_addresses:
          - "10.0.0.1/24"
    primary_ip4: "10.0.0.1/24"     # Optional
```

## Dependencies
- `networktocode.nautobot` collection
- `ansible.netcommon` collection

## Directory Structure
- `defaults/main.yml`: Default configuration variables.
- `handlers/main.yml`: Handlers for the role (currently empty).
- `meta/main.yml`: Metadata for the role, including author and license.
- `tasks/`: Core tasks for processing devices, interfaces, IPs, and prefixes.
  - `main.yml`: Entry point for the role, validates variables and loops over devices.
  - `process_device.yml`: Processes individual device facts.
  - `process_interface.yml`: Manages device interfaces and their IPs.
  - `process_ip.yml`: Handles IP address assignment and conflict resolution.
  - `process_prefix.yml`: Ensures prefixes exist in Nautobot.
  - `parse_ip.yml`: Parses IP addresses using Python's `ipaddress` module.
  - `lookup_and_normalize.yml`: Reusable task for looking up and normalizing API responses.
  - `interface_ip_assignment.yml`: Ensures IP addresses exist and are assigned correctly.
- `tests/test.yml`: Test playbook for running the role on localhost.
- `vars/main.yml`: Additional variables (currently empty).

## Usage
1. **Install Dependencies**:
   ```bash
   ansible-galaxy collection install networktocode.nautobot
   ansible-galaxy collection install ansible.netcommon
   ```

2. **Define Device Facts**:
   Define `device_facts` in your playbook or inventory with the required and optional fields as shown above.

3. **Run the Role**:
   Include the role in your playbook:
   ```yaml
   - hosts: localhost
     roles:
       - role: nautobot_discovery
         vars:
           nautobot_url: "https://nautobot.example.com"
           nautobot_token: "your-api-token"
           device_facts: "{{ device_facts }}"
   ```

4. **Execute the Playbook**:
   ```bash
   ansible-playbook playbook.yml
   ```

## Example Playbook
```yaml
- hosts: localhost
  roles:
    - role: nautobot_discovery
      vars:
        nautobot_url: "https://nautobot.example.com"
        nautobot_token: "your-api-token"
        device_facts:
          - name: "switch01"
            serial_number: "SN98765"
            vendor: "Juniper"
            model: "EX4300"
            platform: "junos"
            location: "DataCenter1"
            device_type: "switch"
            rack: "Rack1"                  # Optional
            position: 10                   # Optional
            face: "front"                  # Optional
            tags: ["core", "prod"]         # Optional
            interfaces:                    # Optional
              - name: "ge-0/0/0"
                type: "1000base-t"
                ip_addresses:
                  - "192.168.1.1/24"
            primary_ip4: "192.168.1.1/24"  # Optional
```

## Notes
- Ensure the Nautobot API is accessible and the provided token has sufficient permissions.
- The role handles IP conflicts by either overwriting existing assignments or allocating the next available IP, based on `allow_ip_overwrite` and `use_next_available_on_conflict`.
- Use `continue_on_error` to allow the role to process all devices even if some fail.
- The role assumes the `ipaddress` Python module is available for IP parsing.

## License
MIT

## Author
Created by Grok, powered by xAI.