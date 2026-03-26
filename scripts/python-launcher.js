const { spawnSync } = require('node:child_process');

function commandExists(cmd, args = ['--version']) {
  const result = spawnSync(cmd, args, { stdio: 'ignore', shell: process.platform === 'win32' });
  return result.status === 0;
}

function detectPythonLauncher() {
  if (commandExists('python')) return 'python';
  if (commandExists('python3')) return 'python3';
  if (process.platform === 'win32' && commandExists('py')) return 'py';
  throw new Error('No Python launcher found. Install Python and ensure `python`, `python3`, or `py` is available in PATH.');
}

module.exports = { detectPythonLauncher };
