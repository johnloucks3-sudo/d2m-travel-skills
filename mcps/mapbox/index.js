#!/usr/bin/env node
const { spawn } = require('child_process');
const path = require('path');

const port = process.argv[2] || 8783;

console.log(`Starting Mapbox MCP Server on port ${port}...`);

// Spawn the actual Mapbox MCP server from node_modules
const mapboxServer = spawn('node', [
  require.resolve('@mapbox/mcp-server/bin/cli.js'),
  '--port', port
], {
  stdio: 'inherit',
  cwd: __dirname
});

mapboxServer.on('error', (err) => {
  console.error('Failed to start Mapbox MCP:', err);
  process.exit(1);
});

process.on('SIGINT', () => {
  mapboxServer.kill();
  process.exit(0);
});
