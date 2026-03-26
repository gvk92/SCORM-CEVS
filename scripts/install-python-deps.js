const { spawnSync } = require('node:child_process');
const { detectPythonLauncher } = require('./python-launcher');

function runInstall(python, reqFile) {
  const args = ['-m', 'pip', 'install', '-r', reqFile];
  return spawnSync(python, args, { stdio: 'inherit', shell: process.platform === 'win32' }).status ?? 1;
}

try {
  const python = detectPythonLauncher();
  const reqFile = process.env.SCORM_USE_LOCKED === '1' ? 'requirements-locked.txt' : 'requirements.txt';

  console.log(`[setup] Python launcher: ${python}`);
  console.log(`[setup] Installing dependencies from ${reqFile}`);

  const status = runInstall(python, reqFile);
  process.exit(status);
} catch (err) {
  console.error(`\n[setup] ${err.message}`);
  process.exit(1);
}
