const { spawnSync } = require('node:child_process');
const { detectPythonLauncher } = require('./python-launcher');

const reload = process.argv.includes('--reload');

try {
  const python = detectPythonLauncher();
  const args = ['-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'];
  if (reload) args.push('--reload');
  const res = spawnSync(python, args, { stdio: 'inherit', shell: process.platform === 'win32' });
  process.exit(res.status ?? 1);
} catch (err) {
  console.error(`\n[start] ${err.message}`);
  process.exit(1);
}
