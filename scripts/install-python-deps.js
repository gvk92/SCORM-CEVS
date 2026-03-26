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
  if (!version) return 'requirements.txt';
  const [major, minor] = version.split('.').map(Number);
  if (major > 3 || (major === 3 && minor >= 14)) {
    return 'requirements-flex.txt';
  }
  return 'requirements.txt';
}

try {
  const python = detectPythonLauncher();
  const version = pythonVersion(python);
  const reqFile = chooseRequirements(version);

  if (reqFile === 'requirements-flex.txt') {
    console.log(`[setup] Detected Python ${version}. Using ${reqFile} for wider wheel compatibility.`);
  }

  const args = ['-m', 'pip', 'install', '-r', reqFile];
  const res = spawnSync(python, args, { stdio: 'inherit', shell: process.platform === 'win32' });
  process.exit(res.status ?? 1);
} catch (err) {
  console.error(`\n[setup] ${err.message}`);
  process.exit(1);
}
