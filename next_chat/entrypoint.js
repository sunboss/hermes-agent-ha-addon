/**
 * NextChat Home Assistant Add-on entrypoint
 * Pure Node.js launcher — zero external dependencies (no bash, no jq).
 */
const fs = require('fs');
const { spawn } = require('child_process');

console.log('[next_chat] Initializing NextChat Add-on (Node.js engine)...');

const configPath = '/data/options.json';
process.env.PORT = '3000';

if (fs.existsSync(configPath)) {
  try {
    const raw = fs.readFileSync(configPath, 'utf8');
    const options = JSON.parse(raw);

    if (options.base_url) {
      process.env.BASE_URL = options.base_url;
      console.log(`[next_chat] Configured BASE_URL: ${options.base_url}`);
    }
    if (options.api_key) {
      process.env.OPENAI_API_KEY = options.api_key;
      console.log('[next_chat] Configured OPENAI_API_KEY (redacted)');
    }
    if (options.access_code) {
      process.env.CODE = options.access_code;
      console.log('[next_chat] Configured access CODE');
    }
    if (options.custom_models) {
      process.env.CUSTOM_MODELS = options.custom_models;
    }
  } catch (err) {
    console.error('[next_chat] Error reading options.json:', err.message);
  }
}

console.log('[next_chat] Starting NextChat server on port 3000...');

const child = spawn('node', ['server.js'], {
  stdio: 'inherit',
  env: process.env,
  cwd: '/app'
});

child.on('exit', (code, signal) => {
  console.log(`[next_chat] Server exited with code ${code} signal ${signal}`);
  process.exit(code || 0);
});
