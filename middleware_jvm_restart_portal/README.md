# Middleware JVM Restart Portal

A Flask + HTML/CSS/JavaScript portal for launching an Ansible Automation Controller / AWX job template to restart selected JVMs.

## Current behavior

- Users log in before reaching the main page.
- LDAP group authorization can be enabled with `LDAP_ENABLED=true`.
- JVM inventory is read from Excel by default.
- The environment dropdown is populated from the Excel `ENVIRONMENT` column.
- JVM dropdown is searchable and displays values as:

```text
JVM_NAME | UNIX_HOST | ENVIRONMENT
```

Example:

```text
test_jvm | test_hostname | UNIT
```

- The restart button is disabled until at least one JVM is selected.
- The portal launches the configured Ansible Controller/AWX job template.
- The portal displays job status, stdout, artifacts, failure details, currently executing jobs, and job history.

## Project layout

```text
middleware_jvm_restart_portal/
├── app.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── README.md
├── data/
│   ├── jvm_inventory.xlsx
│   └── jvms.json                 # legacy JSON fallback only
├── static/
│   ├── css/style.css
│   └── js/app.js
└── templates/
    ├── index.html
    └── login.html
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open:

```text
http://localhost:5000
```

For local testing, keep `LDAP_ENABLED=false`. Any non-empty username/password can log in.

## Required `.env` values

```bash
CONTROLLER_API_BASE=https://controller.example.com/api/controller/v2
CONTROLLER_TOKEN=<controller oauth token>
JOB_TEMPLATE_ID=123
JVM_SOURCE_MODE=excel
JVM_INVENTORY_FILE=./data/jvm_inventory.xlsx
PAYLOAD_VAR_NAME=jvm_restart
RITM_NUMBER=RITMTEST
AUTO_LIMIT_FROM_JVMS=false
PROD_ENVIRONMENTS_ENABLED=false
```

For older AWX/Tower style APIs, use:

```bash
CONTROLLER_API_BASE=https://awx.example.com/api/v2
```

## Excel inventory format

The default source is:

```bash
JVM_SOURCE_MODE=excel
JVM_INVENTORY_FILE=./data/jvm_inventory.xlsx
```

The workbook must have these columns:

```text
ENVIRONMENT | JVM_NAME | UNIX_HOST
```

Example rows:

```text
ENVIRONMENT | JVM_NAME       | UNIX_HOST
UNIT        | test_jvm       | test_hostname
INTG        | claims_server1 | intg-host01.example.com
TRAINING    | training_jvm1  | training-host01.example.com
PRODUCTION  | prod_jvm1      | prod-host01.example.com
```

Header matching is case-insensitive, but keeping the exact names above is recommended.

## Production environment visibility

`TRAINING` and `PRODUCTION` stay as separate environment values. They are not merged.

Visibility is controlled by:

```bash
PROD_ENVIRONMENTS_ENABLED=false
```

When this value is `false`:

- `TRAINING` is hidden from the environment dropdown.
- `PRODUCTION` is hidden from the environment dropdown.
- Their JVMs cannot be selected through the `/api/jvms` endpoint.

When this value is `true`, both values are visible as separate dropdown options:

```text
TRAINING
PRODUCTION
```

## Launch payload

When the user selects one JVM from `UNIT`, the portal sends this payload to Controller:

```json
{
  "extra_vars": {
    "jvm_restart": {
      "ritm_number": "RITMTEST",
      "env": {
        "UNIT": {
          "hosts": {
            "test_hostname": "test_jvm"
          }
        }
      }
    }
  }
}
```

When production environments are enabled and the user selects separate `TRAINING` and `PRODUCTION` rows, the payload keeps them separate:

```yaml
jvm_restart:
  ritm_number: RITMTEST
  env:
    TRAINING:
      hosts:
        training-host01.example.com: training_jvm1
    PRODUCTION:
      hosts:
        prod-host01.example.com: prod_jvm1
```

`ritm_number` defaults to `RITMTEST` for testing. You do not need to track it in the UI.

## LDAP login and group authorization

Local test mode:

```bash
LDAP_ENABLED=false
```

Production LDAP mode:

```bash
LDAP_ENABLED=true
LDAP_SERVER_URI=ldaps://ldap.example.com:636
LDAP_BIND_DN=CN=svc_ldap,OU=Service Accounts,DC=example,DC=com
LDAP_BIND_PASSWORD=<service account password>
LDAP_USER_BASE_DN=OU=Users,DC=example,DC=com
LDAP_USER_FILTER=(sAMAccountName={username})
LDAP_REQUIRED_GROUP_DN=CN=middleware-jvm-restart-users,OU=Groups,DC=example,DC=com
LDAP_GROUP_MEMBER_ATTRIBUTE=member
LDAP_DISPLAY_NAME_ATTRIBUTE=cn
```

Only users in `LDAP_REQUIRED_GROUP_DN` can access the main portal when LDAP is enabled.

## Job history

The portal stores launch history in SQLite:

```bash
HISTORY_DB_PATH=./data/history.sqlite3
HISTORY_LIMIT=50
```

The history table tracks launch time, username, Controller job ID, status, selected JVMs, and failure/debug message when available.

The **Currently Executing Jobs** section shows active jobs launched from this portal by all logged-in users. It refreshes every 15 seconds.

## Example Ansible playbook input handling

```yaml
- name: Restart selected JVMs
  hosts: all
  gather_facts: false
  vars:
    jvm_restart:
      ritm_number: RITMTEST
      env: {}

  tasks:
    - name: Show requested restart payload
      debug:
        var: jvm_restart

    - name: Show environment-level restart map
      debug:
        msg: "Environment {{ item.key }} hosts {{ item.value.hosts }}"
      loop: "{{ jvm_restart.env | dict2items }}"
```

## Optional legacy JSON or REST API source

Excel is the default source. The app still supports the earlier JSON and REST API modes for fallback testing.

```bash
JVM_SOURCE_MODE=json
```

or:

```bash
JVM_SOURCE_MODE=api
JVM_RESOURCE_URL=https://inventory-resource.example.com/api/jvms
JVM_RESOURCE_TOKEN=<optional bearer token>
```

## Production deployment with Gunicorn

```bash
pip install gunicorn
gunicorn -w 3 -b 0.0.0.0:5000 app:app
```

Use NGINX or Apache as a TLS reverse proxy in front of the Flask app.

## Docker run

```bash
docker build -t middleware-jvm-restart-portal .
docker run --env-file .env -p 5000:5000 middleware-jvm-restart-portal
```
