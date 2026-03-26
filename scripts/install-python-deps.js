const { spawnSync } = require('node:child_process');
const { detectPythonLauncher } = require('./python-launcher');

try {
  const python = detectPythonLauncher();
  const args = python === 'py'
    ? ['-m', 'pip', 'install', '-r', 'requirements.txt']
    : ['-m', 'pip', 'install', '-r', 'requirements.txt'];
  const res = spawnSync(python, args, { stdio: 'inherit', shell: process.platform === 'win32' });
  process.exit(res.status ?? 1);
} catch (err) {
  console.error(`\n[setup] ${err.message}`);
  process.exit(1);
}
