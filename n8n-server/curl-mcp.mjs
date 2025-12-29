#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const server = new Server(
  {
    name: "curl-bridge-server",
    version: "1.0.0",
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
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "curl") {
    const { url, method = "GET", headers = {}, body } = request.params.arguments;

    try {
      const response = await fetch(url, {
        method,
        headers,
        body: body ? String(body) : undefined,
      });

      const responseText = await response.text();
      const responseHeaders = {};
      response.headers.forEach((value, key) => {
        responseHeaders[key] = value;
      });

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              {
                status: response.status,
                statusText: response.statusText,
                headers: responseHeaders,
                body: responseText,
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error executing request: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }

  throw new Error(`Tool not found: ${request.params.name}`);
});

const transport = new StdioServerTransport();
await server.connect(transport);
