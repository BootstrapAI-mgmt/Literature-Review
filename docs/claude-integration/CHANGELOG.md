# Changelog

All notable changes to the Claude Desktop integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Planned
- n8n workflow execution from Claude
- GitHub Issues/PR management
- Automated documentation pipelines

---

## [0.1.0] - 2024-12-23

### Added
- Initial Claude Desktop integration architecture assessment
- Created `claude_desktop_config.json` with n8n and GitHub MCP server configurations
- Updated Filesystem MCP to include Literature-Review repository access
- Created `/docs/claude-integration/` documentation folder with:
  - `README.md` - Integration overview
  - `ARCHITECTURE.md` - Technical architecture documentation
  - `ROADMAP.md` - Implementation phases and milestones
  - `SETUP.md` - Configuration and setup guide
  - `CHANGELOG.md` - This file

### Configured
- Desktop Commander MCP - Full filesystem access
- Filesystem MCP - Added Literature-Review repository to allowed directories
- n8n MCP Server - Template configuration (awaiting API key)
- GitHub MCP Server - Template configuration (awaiting PAT)

### Documented
- System architecture with component diagrams
- MCP server configurations and capabilities
- 5-phase implementation roadmap
- Step-by-step setup instructions
- Security best practices

### Dependencies
- `@leonardsellem/n8n-mcp-server` - n8n workflow management
- `@modelcontextprotocol/server-github` - GitHub API integration

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 0.1.0 | 2024-12-23 | Initial setup and documentation |

---

## How to Update This Log

When making changes to the Claude integration:

1. Add entry under `[Unreleased]` section
2. Use categories: Added, Changed, Deprecated, Removed, Fixed, Security
3. When releasing, move entries to new version section with date
4. Keep descriptions concise but informative

---

*Maintained by Claude Desktop Integration Team*
