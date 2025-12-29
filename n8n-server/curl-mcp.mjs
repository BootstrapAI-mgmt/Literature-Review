#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// n8n Cloud Configuration
const N8N_BASE_URL = "https://gitlitreview.app.n8n.cloud/webhook";

const server = new Server(
  {
    name: "curl-bridge-server",
    version: "2.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "curl",
        description: "Make an HTTP request (like curl) from the local machine. Use this to bypass proxy restrictions or access local services.",
        inputSchema: {
          type: "object",
          properties: {
            url: {
              type: "string",
              description: "The URL to request",
            },
            method: {
              type: "string",
              description: "HTTP method (GET, POST, PUT, DELETE, etc.)",
              default: "GET",
            },
            headers: {
              type: "object",
              description: "HTTP headers",
            },
            body: {
              type: "string",
              description: "Request body (for POST/PUT/etc). If JSON, pass as stringified JSON.",
            },
          },
          required: ["url"],
        },
      },
      // n8n Distributor Status
      {
        name: "n8n_status",
        description: "Get the current status of the n8n Distributor workflow including pending tasks, in-progress task, and completion history.",
        inputSchema: {
          type: "object",
          properties: {},
          required: [],
        },
      },
      // n8n Distributor Reset
      {
        name: "n8n_reset",
        description: "Reset the n8n Distributor state, clearing all pending and in-progress tasks. Use with caution.",
        inputSchema: {
          type: "object",
          properties: {
            confirm: {
              type: "boolean",
              description: "Must be true to confirm the reset operation",
            },
          },
          required: ["confirm"],
        },
      },
      // n8n State Reconciliation
      {
        name: "n8n_reconcile",
        description: "Trigger the State Reconciliation workflow to scan for documentation mismatches and generate correction tasks.",
        inputSchema: {
          type: "object",
          properties: {
            scan_type: {
              type: "string",
              description: "Type of scan: 'quick' or 'deep' (default: deep)",
              default: "deep",
            },
          },
          required: [],
        },
      },
      // n8n Submit Task
      {
        name: "n8n_submit_task",
        description: "Submit a task directly to the n8n Distributor for processing.",
        inputSchema: {
          type: "object",
          properties: {
            document: {
              type: "string",
              description: "Path to the document (e.g., 'docs/README.md')",
            },
            update_type: {
              type: "string",
              description: "Type of update: STATUS_UPDATE, CONTENT_REVIEW, MISMATCH_CORRECTION",
            },
            description: {
              type: "string",
              description: "Description of the task",
            },
            priority: {
              type: "number",
              description: "Task priority (1=highest, 5=lowest)",
              default: 3,
            },
          },
          required: ["document", "update_type", "description"],
        },
      },
      // n8n Health Check
      {
        name: "n8n_health",
        description: "Check if all n8n workflows are responsive and healthy.",
        inputSchema: {
          type: "object",
          properties: {},
          required: [],
        },
      },
      // Claude-Antigravity Bridge: Send message to workflow
      {
        name: "antigravity_send",
        description: "Send a message or command from Claude to Antigravity via n8n webhook. This enables Claude to communicate with Antigravity agents.",
        inputSchema: {
          type: "object",
          properties: {
            message_type: {
              type: "string",
              description: "Type of message: 'command', 'query', 'notification', 'task_request'",
            },
            payload: {
              type: "object",
              description: "Message payload - can contain any structured data for Antigravity",
            },
            callback_expected: {
              type: "boolean",
              description: "Whether Claude expects a callback response from Antigravity",
              default: false,
            },
          },
          required: ["message_type", "payload"],
        },
      },
      // Claude-Antigravity Bridge: Query Antigravity status
      {
        name: "antigravity_query",
        description: "Query the Antigravity system status and capabilities through the n8n bridge.",
        inputSchema: {
          type: "object",
          properties: {
            query_type: {
              type: "string",
              description: "Type of query: 'status', 'capabilities', 'active_tasks', 'history'",
            },
          },
          required: ["query_type"],
        },
      },
    ],
  };
});

// Helper function for HTTP requests
async function makeRequest(url, method = "GET", headers = {}, body = null) {
  try {
    const options = {
      method,
      headers: { "Content-Type": "application/json", ...headers },
    };
    if (body) {
      options.body = typeof body === "string" ? body : JSON.stringify(body);
    }
    
    const response = await fetch(url, options);
    const responseText = await response.text();
    
    let responseData;
    try {
      responseData = JSON.parse(responseText);
    } catch {
      responseData = responseText;
    }
    
    return {
      status: response.status,
      statusText: response.statusText,
      data: responseData,
    };
  } catch (error) {
    return { error: error.message };
  }
}

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  // Generic curl handler
  if (name === "curl") {
    const { url, method = "GET", headers = {}, body } = args;
    const result = await makeRequest(url, method, headers, body);
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      isError: !!result.error,
    };
  }

  // n8n Status handler
  if (name === "n8n_status") {
    const result = await makeRequest(`${N8N_BASE_URL}/distributor-status`);
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      isError: !!result.error,
    };
  }

  // n8n Reset handler
  if (name === "n8n_reset") {
    if (!args.confirm) {
      return {
        content: [{ type: "text", text: "Reset not confirmed. Set confirm: true to proceed." }],
        isError: true,
      };
    }
    const result = await makeRequest(`${N8N_BASE_URL}/distributor-reset`, "POST");
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      isError: !!result.error,
    };
  }

  // n8n Reconciliation handler
  if (name === "n8n_reconcile") {
    const payload = { scan_type: args.scan_type || "deep" };
    const result = await makeRequest(`${N8N_BASE_URL}/state-reconciliation`, "POST", {}, payload);
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      isError: !!result.error,
    };
  }

  // n8n Submit Task handler
  if (name === "n8n_submit_task") {
    const taskId = `claude-task-${Date.now()}`;
    const payload = {
      update_list_id: `claude-${Date.now()}`,
      source: "claude-bridge",
      trigger: { type: "claude", message: "Task submitted via Claude MCP bridge" },
      tasks: [{
        task_id: taskId,
        document: args.document,
        update_type: args.update_type,
        description: args.description,
        priority: args.priority || 3,
      }],
    };
    const result = await makeRequest(`${N8N_BASE_URL}/task-distributor`, "POST", {}, payload);
    return {
      content: [{ type: "text", text: JSON.stringify({ task_id: taskId, ...result }, null, 2) }],
      isError: !!result.error,
    };
  }

  // n8n Health Check handler
  if (name === "n8n_health") {
    const endpoints = [
      { name: "Distributor", url: `${N8N_BASE_URL}/distributor-status` },
      { name: "State Reconciliation", url: `${N8N_BASE_URL}/state-reconciliation` },
    ];
    
    const results = await Promise.all(
      endpoints.map(async (ep) => {
        const start = Date.now();
        const result = await makeRequest(ep.url, "GET");
        return {
          name: ep.name,
          status: result.status === 200 ? "healthy" : "unhealthy",
          response_time_ms: Date.now() - start,
          details: result.error || result.statusText,
        };
      })
    );
    
    const allHealthy = results.every((r) => r.status === "healthy");
    return {
      content: [{
        type: "text",
        text: JSON.stringify({ overall: allHealthy ? "healthy" : "degraded", services: results }, null, 2),
      }],
      isError: !allHealthy,
    };
  }

  // Antigravity Send handler
  if (name === "antigravity_send") {
    const payload = {
      source: "claude",
      timestamp: new Date().toISOString(),
      message_type: args.message_type,
      payload: args.payload,
      callback_expected: args.callback_expected || false,
      correlation_id: `claude-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    };
    const result = await makeRequest(`${N8N_BASE_URL}/claude-antigravity-bridge`, "POST", {}, payload);
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      isError: !!result.error,
    };
  }

  // Antigravity Query handler
  if (name === "antigravity_query") {
    const payload = {
      source: "claude",
      query_type: args.query_type,
      timestamp: new Date().toISOString(),
    };
    const result = await makeRequest(`${N8N_BASE_URL}/antigravity-status`, "POST", {}, payload);
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      isError: !!result.error,
    };
  }

  throw new Error(`Tool not found: ${name}`);
});

const transport = new StdioServerTransport();
await server.connect(transport);
