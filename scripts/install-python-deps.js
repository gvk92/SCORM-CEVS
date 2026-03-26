const { spawnSync } = require('node:child_process');
const { detectPythonLauncher } = require('./python-launcher');

function pythonVersion(python) {
  const res = spawnSync(
    python,
    ['-c', 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'],
    { encoding: 'utf-8', shell: process.platform === 'win32' }
  );
  if (res.status !== 0) return null;
  return res.stdout.trim();
}

function chooseRequirements(version) {
  if (!version) return 'requirements-flex.txt';
  const [major, minor] = version.split('.').map(Number);
  if (major > 3 || (major === 3 && minor >= 14)) return 'requirements-flex.txt';
  return 'requirements.txt';
}

function runInstall(python, reqFile) {
  const args = ['-m', 'pip', 'install', '-r', reqFile];
  return spawnSync(python, args, { stdio: 'inherit', shell: process.platform === 'win32' }).status ?? 1;
}

try {
  const python = detectPythonLauncher();
  const version = pythonVersion(python);
  let reqFile = chooseRequirements(version);

  console.log(`[setup] Python launcher: ${python}${version ? ` (${version})` : ''}`);
  console.log(`[setup] Installing dependencies from ${reqFile}`);

  let status = runInstall(python, reqFile);

  // Safety net: if pinned requirements fail (commonly on very new Python versions), retry with flexible deps.
  if (status !== 0 && reqFile !== 'requirements-flex.txt') {
    reqFile = 'requirements-flex.txt';
    console.log(`[setup] Retry with ${reqFile} for wider wheel compatibility...`);
    status = runInstall(python, reqFile);
  }

  process.exit(status);
} catch (err) {
  console.error(`\n[setup] ${err.message}`);
  process.exit(1);
}
