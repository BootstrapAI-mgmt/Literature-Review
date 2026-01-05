import os
import requests
import json
import base64
import re
import time

# n8n API configuration
N8N_API_URL = "http://localhost:5678/api/v1"
N8N_API_KEY = os.environ.get("N8N_API_KEY", "")

# Repository configuration from environment
env_vars = {
    "REPO_OWNER": os.environ.get("REPO_OWNER", "BootstrapAI-mgmt"),
    "REPO_NAME": os.environ.get("REPO_NAME", "Literature-Review"),
    "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", ""),
    "N8N_BASE_URL": os.environ.get("N8N_BASE_URL", "http://localhost:5678/webhook")
}

def get_workflows():
    headers = {"X-N8N-API-KEY": N8N_API_KEY}
    response = requests.get(f"{N8N_API_URL}/workflows", headers=headers)
    if response.status_code == 200:
        return response.json().get('data', [])
    print(f"Error fetching workflows: {response.status_code}")
    return []

def patch_node_code(nodes):
    """Patch specific node code logic."""
    for node in nodes:
        # Patch Agent's Parse Webhook Data
        if node.get('name') == 'Parse Webhook Data' and node.get('type') == 'n8n-nodes-base.code':
            node['parameters']['jsCode'] = """
const json = $input.first().json; 
console.log('AGENT RECEIVED:', JSON.stringify(json));
const body = json.body || json;

const deepParse = (obj) => {
  if (typeof obj === 'string') {
    try { return JSON.parse(obj); } catch (e) { return obj; }
  }
  if (obj && typeof obj === 'object') {
    const newObj = Array.isArray(obj) ? [] : {};
    for (const key in obj) { newObj[key] = deepParse(obj[key]); }
    return newObj;
  }
  return obj;
};

const parsedData = deepParse(body);
const task = parsedData.task || {};
const trigger = parsedData.trigger || {};
const list_id = parsedData.list_id || 'unknown';

if (task && task.target && !task.document) {
  task.document = task.target;
}

return { task, trigger, list_id };
"""
        
        # Patch Get Domains in Staleness (aggregation)
        if node.get('name') == 'Get Domains' and node.get('type') == 'n8n-nodes-base.code':
            code = node['parameters'].get('jsCode', '')
            old_loop = r"for (const doc of matrix.documents || []) {\n     const domainEntry = domains.find(d => d.domain === doc.owner);\n     if (domainEntry && doc.staleness_indicators) {\n       domainEntry.staleness_indicators.push(...doc.staleness_indicators);\n     }\n   }"
            # Simplified matching for robustness
            if "domainEntry.staleness_indicators.push" in code and "doc.last_reviewed" not in code:
                new_loop = """   for (const doc of matrix.documents || []) {
     const domainEntry = domains.find(d => d.domain === doc.owner);
     if (domainEntry) {
       if (doc.staleness_indicators) { domainEntry.staleness_indicators.push(...doc.staleness_indicators); }
       if (doc.last_reviewed) {
         if (!domainEntry.last_reviewed || doc.last_reviewed > domainEntry.last_reviewed) {
           domainEntry.last_reviewed = doc.last_reviewed;
         }
       }
     }
   }"""
                # We'll just replace the whole loop section if we can identify it
                header = "// Add staleness_indicators from document entries"
                if header in code:
                   code_parts = code.split(header)
                   # Rebuild with new loop
                   # Assuming the loop follows the header
                   suffix = code_parts[1].split("   // Deduplicate indicators")[1]
                   node['parameters']['jsCode'] = code_parts[0] + header + "\n" + new_loop + "\n\n   // Deduplicate indicators" + suffix

        # Patch Find Affected Docs in Reconciliation (Base64 handling)
        if node.get('name') == 'Find Affected Docs' and node.get('type') == 'n8n-nodes-base.code':
            code = node['parameters'].get('jsCode', '')
            old_line = "const matrix = typeof matrixRaw.data === 'string' ? JSON.parse(matrixRaw.data) : matrixRaw;"
            new_line = "const matrix = matrixRaw.content && matrixRaw.encoding === 'base64' ? JSON.parse(Buffer.from(matrixRaw.content, 'base64').toString()) : (typeof matrixRaw.data === 'string' ? JSON.parse(matrixRaw.data) : matrixRaw);"
            if old_line in code:
                node['parameters']['jsCode'] = code.replace(old_line, new_line)

        # Patch Distributor webhook response
        if node.get('name') == 'Send To Agent' and node.get('type') == 'n8n-nodes-base.httpRequest':
            node['parameters']['specifyBody'] = 'json'
            node['parameters']['jsonBody'] = '={{ { task: $json.task, trigger: $json.trigger, list_id: $json.list_id } }}'

        # Patch Staleness Assessment prompt
        if node.get('name') == 'Staleness Assessment':
            params = node.get('parameters', {})
            if 'options' in params and 'systemMessage' in params['options']:
                params['options']['systemMessage'] = params['options']['systemMessage'].replace(
                    'as an array of strings',
                    'as an array of objects with fields: task_id, document, description, update_type'
                )

        # Patch Structured Output Parser schema
        if node.get('name') == 'Structured Output Parser':
            params = node.get('parameters', {})
            if 'inputSchema' in params:
                schema = json.loads(params['inputSchema'])
                if 'update_tasks' in schema.get('properties', {}):
                    schema['properties']['update_tasks']['items'] = {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string"},
                            "document": {"type": "string"},
                            "description": {"type": "string"},
                            "update_type": {"type": "string"}
                        },
                        "required": ["document", "description"]
                    }
                    params['inputSchema'] = json.dumps(schema, indent=2)

def inject_auth(nodes):
    """Inject GitHub token into HTTP nodes and force override existing auth."""
    for node in nodes:
        if node.get('type') == 'n8n-nodes-base.httpRequest':
            params = node.get('parameters', {})
            url = str(params.get('url', ''))
            
            if 'github' in url.lower():
                # Handle headersUi
                if 'headersUi' not in params:
                    params['headersUi'] = {'parameterHeaders': []}
                headers_ui = params['headersUi'].get('parameterHeaders', [])
                
                # Force override or add Authorization
                auth_header = next((h for h in headers_ui if h.get('name', '').lower() == 'authorization'), None)
                if auth_header:
                    auth_header['value'] = f"token {env_vars['GITHUB_TOKEN']}"
                else:
                    headers_ui.append({'name': 'Authorization', 'value': f"token {env_vars['GITHUB_TOKEN']}"})
                
                if not any(h.get('name', '').lower() == 'accept' for h in headers_ui):
                    headers_ui.append({'name': 'Accept', 'value': 'application/json'})

                # Handle headerParameters (often used in older or specific node versions)
                if 'headerParameters' in params:
                    headers_param = params['headerParameters'].get('parameters', [])
                    auth_param = next((p for p in headers_param if p.get('name', '').lower() == 'authorization'), None)
                    if auth_param:
                        auth_param['value'] = f"token {env_vars['GITHUB_TOKEN']}"
                    else:
                        headers_param.append({'name': 'Authorization', 'value': f"token {env_vars['GITHUB_TOKEN']}"})
                
                params['sendHeaders'] = True
                params['authentication'] = 'none'
                if 'credentials' in node:
                    del node['credentials']

def solve_env_templates(obj):
    """Recursively replace env templates in object."""
    if isinstance(obj, str):
        for key, value in env_vars.items():
            obj = obj.replace(f"{{{{ env.{key} }}}}", value)
        # Redirection from legacy n8n cloud URL to local n8n
        legacy = "https://gitlitreview.app.n8n.cloud"
        if legacy + "/webhook" in obj:
            obj = obj.replace(legacy + "/webhook", env_vars["N8N_BASE_URL"])
        obj = obj.replace(legacy, env_vars["N8N_BASE_URL"])
        return obj
    elif isinstance(obj, dict):
        return {k: solve_env_templates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [solve_env_templates(i) for i in obj]
    return obj

def update_workflow(workflow_id, workflow_data, name):
    headers = {"X-N8N-API-KEY": N8N_API_KEY}
    
    # Remove hacky ad-hoc patching, rely on file content being correct
    # patch_node_code(workflow_data['nodes'])
    # inject_auth(workflow_data['nodes'])
    
    # Resolve env vars (primary mechanism for credentials and URLs)
    workflow_data = solve_env_templates(workflow_data)
    
    # Send update
    payload = {
        "name": name,
        "nodes": workflow_data['nodes'],
        "connections": workflow_data['connections'],
        "settings": workflow_data.get('settings', {})
    }
    
    url = f"{N8N_API_URL}/workflows/{workflow_id}"
    response = requests.put(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"Successfully updated workflow: {name} ({workflow_id})")
    else:
        print(f"Error updating workflow {name}: {response.status_code}")
        print(response.text)

def main():
    if not N8N_API_KEY:
        print("Error: N8N_API_KEY not set.")
        return

    workflows = get_workflows()
    print(f"Found {len(workflows)} workflows.")
    
    for filename in os.listdir("n8n-server/workflows"):
        if not filename.endswith(".json"): continue
        with open(os.path.join("n8n-server/workflows", filename), 'r', encoding='utf8') as f:
            data = json.load(f)
            
        blueprint = data.get('activeVersion') or data
        name = data.get('name') or blueprint.get('name')
        id_val = data.get('id') or blueprint.get('id')
        
        existing = next((w for w in workflows if w['name'] == name or w['id'] == id_val), None)
        if existing:
            update_workflow(existing['id'], blueprint, name)
        else:
            print(f"Workflow '{name}' not found.")

if __name__ == "__main__":
    main()
