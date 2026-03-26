const { spawnSync } = require('node:child_process');
const { detectPythonLauncher } = require('./python-launcher');

const reload = process.argv.includes('--reload');
const host = process.env.SCORM_HOST || '127.0.0.1';
const port = process.env.SCORM_PORT || '8000';

try {
  const python = detectPythonLauncher();
  const args = ['-m', 'uvicorn', 'app.main:app', '--host', host, '--port', port];
  if (reload) args.push('--reload');

  console.log(`[start] Launching on http://${host}:${port}`);
  if (host === '0.0.0.0') {
    console.log('[start] Note: open http://127.0.0.1:' + port + ' locally, not http://0.0.0.0:' + port);
  }

  const res = spawnSync(python, args, { stdio: 'inherit', shell: process.platform === 'win32' });
  process.exit(res.status ?? 1);
} catch (err) {
  console.error(`\n[start] ${err.message}`);
  process.exit(1);
}
