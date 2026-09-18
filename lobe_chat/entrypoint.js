/**
 * LobeChat Home Assistant Add-on entrypoint
 * Pure Node.js launcher — zero external dependencies (no bash, no jq).
 */
const fs = require('fs');
const crypto = require('crypto');
const { spawn } = require('child_process');

console.log('[lobe_chat] Initializing LobeChat Add-on (Node.js engine)...');

const configPath = '/data/options.json';
process.env.PORT = '3210';

if (fs.existsSync(configPath)) {
  try {
    const raw = fs.readFileSync(configPath, 'utf8');
    const options = JSON.parse(raw);

    if (options.openai_proxy_url) {
      process.env.OPENAI_PROXY_URL = options.openai_proxy_url;
      console.log(`[lobe_chat] Configured OPENAI_PROXY_URL: ${options.openai_proxy_url}`);
    }
    if (options.openai_api_key) {
      process.env.OPENAI_API_KEY = options.openai_api_key;
      console.log('[lobe_chat] Configured OPENAI_API_KEY (redacted)');
    }
    if (options.access_code) {
      process.env.ACCESS_CODE = options.access_code;
      console.log('[lobe_chat] Configured ACCESS_CODE protection');
    }
    if (options.default_model) {
      process.env.DEFAULT_MODEL = options.default_model;
    }
  } catch (err) {
    console.error('[lobe_chat] Error reading options.json:', err.message);
  }
}

// Generate persistent or runtime key vault secret
if (!process.env.KEY_VAULTS_SECRET) {
  process.env.KEY_VAULTS_SECRET = crypto.randomBytes(32).toString('base64');
}

console.log('[lobe_chat] Starting LobeChat server on port 3210...');

// Start node server.js from /app
const child = spawn('node', ['/app/server.js'], {
  stdio: 'inherit',
  env: process.env,
  cwd: '/app'
});

child.on('exit', (code, signal) => {
  console.log(`[lobe_chat] Server exited with code ${code} signal ${signal}`);
  process.exit(code || 0);
});
