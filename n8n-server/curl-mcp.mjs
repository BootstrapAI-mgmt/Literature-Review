#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// ============================================================================
// Configuration
// ============================================================================
const N8N_CLOUD_URL = "https://gitlitreview.app.n8n.cloud";
const N8N_LOCAL_URL = "http://localhost:5678";

// Default to cloud, can be overridden via environment
const N8N_BASE_URL = process.env.N8N_WEBHOOK_URL || N8N_CLOUD_URL;

// ============================================================================
// Helper Functions
// ============================================================================
async function makeRequest(url, method = "GET", headers = {}, body = null) {
  const response = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json", ...headers },
    body: body ? (typeof body === "string" ? body : JSON.stringify(body)) : undefined,
  });

  const responseText = await response.text();
  let parsedBody;
  try {
    parsedBody = JSON.parse(responseText);
  } catch {
    parsedBody = responseText;
  }

  return {
    status: response.status,
    statusText: response.statusText,
    body: parsedBody,
  };
}

function formatResponse(result) {
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(result, null, 2),
      },
    ],
  };
}

function formatError(error) {
  return {
    content: [
      {
        type: "text",
        text: `Error: ${error.message}`,
      },
    ],
    isError: true,
  };
}

// ============================================================================
// Tool Definitions
// ============================================================================
const tools = [
  // Generic curl tool
  {
    name: "curl",
    description: "Make an HTTP request (like curl) from the local machine. Use this to bypass proxy restrictions or access local services.",
    inputSchema: {
      type: "object",
      properties: {
        url: { type: "string", description: "The URL to request" },
        method: { type: "string", description: "HTTP method (GET, POST, PUT, DELETE, etc.)", default: "GET" },
        headers: { type: "object", description: "HTTP headers" },
        body: { type: "string", description: "Request body (for POST/PUT/etc). If JSON, pass as stringified JSON." },
      },
      required: ["url"],
    },
  },

  // n8n Distributor Status
  {
    name: "n8n_status",
    description: "Get the current status of the n8n Doc Chain Distributor including pending tasks, in-progress task, and completion stats.",
    inputSchema: {
      type: "object",
      properties: {
        use_local: { type: "boolean", description: "Use local n8n instead of cloud (default: false)", default: false },
      },
    },
  },

  // n8n Distributor Reset
  {
    name: "n8n_reset",
    description: "Reset the n8n Distributor state, clearing all pending and in-progress tasks. Use with caution.",
    inputSchema: {
      type: "object",
      properties: {
        use_local: { type: "boolean", description: "Use local n8n instead of cloud (default: false)", default: false },
        confirm: { type: "boolean", description: "Must be true to execute reset", default: false },
      },
      required: ["confirm"],
    },
  },

  // Trigger State Reconciliation
  {
    name: "n8n_reconcile",
    description: "Trigger the State Reconciliation workflow to scan for documentation mismatches and generate correction tasks.",
    inputSchema: {
      type: "object",
      properties: {
        use_local: { type: "boolean", description: "Use local n8n instead of cloud (default: false)", default: false },
        scan_type: { type: "string", description: "Type of scan: 'quick' or 'deep' (default: deep)", default: "deep" },
      },
    },
  },

  // Submit Task to Distributor
  {
    name: "n8n_submit_task",
    description: "Submit a documentation task to the n8n Distributor for processing by the Agent workflow.",
    inputSchema: {
      type: "object",
      properties: {
        use_local: { type: "boolean", description: "Use local n8n instead of cloud (default: false)", default: false },
        task_id: { type: "string", description: "Unique identifier for this task" },
        document: { type: "string", description: "Path to the document (e.g., 'docs/README.md')" },
        update_type: { type: "string", description: "Type of update: STATUS_UPDATE, CONTENT_REFRESH, REVIEW_NEEDED, etc." },
        description: { type: "string", description: "Description of what needs to be done" },
        priority: { type: "number", description: "Priority level (1=highest, 5=lowest)", default: 3 },
      },
      required: ["task_id", "document", "update_type", "description"],
    },
  },

  // Trigger Staleness Review
  {
    name: "n8n_staleness_check",
    description: "Trigger the Staleness Review workflow to identify outdated documentation.",
    inputSchema: {
      type: "object",
      properties: {
        use_local: { type: "boolean", description: "Use local n8n instead of cloud (default: false)", default: false },
      },
    },
  },

  // Claude Feedback Loop - Send message to n8n for Antigravity processing
  {
    name: "n8n_claude_message",
    description: "Send a message from Claude to n8n for processing by Antigravity or other agents. Part of the Claude ↔ n8n ↔ Antigravity feedback loop.",
    inputSchema: {
      type: "object",
      properties: {
        use_local: { type: "boolean", description: "Use local n8n instead of cloud (default: false)", default: false },
        message_type: { 
          type: "string", 
          description: "Type of message: 'task_request', 'status_query', 'feedback', 'instruction'",
          enum: ["task_request", "status_query", "feedback", "instruction"]
        },
        payload: { type: "object", description: "Message payload with context and data" },
        callback_requested: { type: "boolean", description: "Whether to request a callback response", default: true },
        priority: { type: "string", description: "Message priority: 'high', 'normal', 'low'", default: "normal" },
      },
      required: ["message_type", "payload"],
    },
  },

  // Get execution history summary
  {
    name: "n8n_history",
    description: "Get a summary of recent n8n workflow executions for debugging and monitoring.",
    inputSchema: {
      type: "object",
      properties: {
        use_local: { type: "boolean", description: "Use local n8n instead of cloud (default: false)", default: false },
        workflow: { type: "string", description: "Filter by workflow name (optional)", default: "" },
        limit: { type: "number", description: "Number of executions to retrieve", default: 10 },
      },
    },
  },
];

// ============================================================================
// Tool Handlers
// ============================================================================
async function handleCurl(args) {
  const { url, method = "GET", headers = {}, body } = args;
  const result = await makeRequest(url, method, headers, body);
  return formatResponse(result);
}

async function handleN8nStatus(args) {
  const baseUrl = args.use_local ? N8N_LOCAL_URL : N8N_BASE_URL;
  const result = await makeRequest(`${baseUrl}/webhook/distributor-status`);
  return formatResponse({
    source: args.use_local ? "local" : "cloud",
    ...result,
  });
}

async function handleN8nReset(args) {
  if (!args.confirm) {
    return formatResponse({
      error: "Reset requires confirm: true",
      message: "This will clear all pending and in-progress tasks. Set confirm: true to proceed.",
    });
  }
  const baseUrl = args.use_local ? N8N_LOCAL_URL : N8N_BASE_URL;
  const result = await makeRequest(`${baseUrl}/webhook/distributor-reset`, "POST");
  return formatResponse({
    source: args.use_local ? "local" : "cloud",
    action: "reset",
    ...result,
  });
}

async function handleN8nReconcile(args) {
  const baseUrl = args.use_local ? N8N_LOCAL_URL : N8N_BASE_URL;
  const result = await makeRequest(
    `${baseUrl}/webhook/state-reconciliation`,
    "POST",
    {},
    { scan_type: args.scan_type || "deep" }
  );
  return formatResponse({
    source: args.use_local ? "local" : "cloud",
    action: "reconciliation",
    ...result,
  });
}

async function handleN8nSubmitTask(args) {
  const baseUrl = args.use_local ? N8N_LOCAL_URL : N8N_BASE_URL;
  const payload = {
    update_list_id: `claude-${Date.now()}`,
    source: "claude-mcp-bridge",
    trigger: {
      type: "claude_request",
      message: "Task submitted via Claude MCP bridge",
    },
    tasks: [
      {
        task_id: args.task_id,
        document: args.document,
        update_type: args.update_type,
        description: args.description,
        priority: args.priority || 3,
      },
    ],
  };
  const result = await makeRequest(`${baseUrl}/webhook/task-distributor`, "POST", {}, payload);
  return formatResponse({
    source: args.use_local ? "local" : "cloud",
    action: "submit_task",
    task_id: args.task_id,
    ...result,
  });
}

async function handleN8nStalenessCheck(args) {
  const baseUrl = args.use_local ? N8N_LOCAL_URL : N8N_BASE_URL;
  const result = await makeRequest(`${baseUrl}/webhook/staleness-review`, "POST");
  return formatResponse({
    source: args.use_local ? "local" : "cloud",
    action: "staleness_check",
    ...result,
  });
}

async function handleN8nClaudeMessage(args) {
  const baseUrl = args.use_local ? N8N_LOCAL_URL : N8N_BASE_URL;
  const payload = {
    source: "claude",
    message_type: args.message_type,
    payload: args.payload,
    callback_requested: args.callback_requested !== false,
    priority: args.priority || "normal",
    timestamp: new Date().toISOString(),
    session_id: `claude-session-${Date.now()}`,
  };
  const result = await makeRequest(`${baseUrl}/webhook/claude-bridge`, "POST", {}, payload);
  return formatResponse({
    source: args.use_local ? "local" : "cloud",
    action: "claude_message",
    message_type: args.message_type,
    ...result,
  });
}

async function handleN8nHistory(args) {
  // This requires n8n API access, so we provide guidance
  return formatResponse({
    source: args.use_local ? "local" : "cloud",
    action: "history",
    note: "Use the n8n MCP server (n8n:list_executions) for detailed execution history.",
    hint: "This tool is a placeholder - full history requires n8n API authentication.",
    suggestion: "Try: n8n:list_executions with limit parameter",
  });
}

// ============================================================================
// Server Setup
// ============================================================================
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
  return { tools };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "curl":
        return await handleCurl(args);
      case "n8n_status":
        return await handleN8nStatus(args);
      case "n8n_reset":
        return await handleN8nReset(args);
      case "n8n_reconcile":
        return await handleN8nReconcile(args);
      case "n8n_submit_task":
        return await handleN8nSubmitTask(args);
      case "n8n_staleness_check":
        return await handleN8nStalenessCheck(args);
      case "n8n_claude_message":
        return await handleN8nClaudeMessage(args);
      case "n8n_history":
        return await handleN8nHistory(args);
      default:
        throw new Error(`Tool not found: ${name}`);
    }
  } catch (error) {
    return formatError(error);
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
