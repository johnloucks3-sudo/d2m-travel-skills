#!/usr/bin/env node
const { spawn } = require('child_process');
const path = require('path');

const port = process.argv[2] || 8780;

console.log(`Starting Apify MCP Server on port ${port}...`);

// Spawn the actual Apify MCP server from node_modules
const apifyServer = spawn('node', [
  require.resolve('@apify/actors-mcp-server/bin/cli.js'),
  '--port', port
], {
  stdio: 'inherit',
  cwd: __dirname
});

apifyServer.on('error', (err) => {
  console.error('Failed to start Apify MCP:', err);
  process.exit(1);
});

process.on('SIGINT', () => {
  apifyServer.kill();
  process.exit(0);
});
