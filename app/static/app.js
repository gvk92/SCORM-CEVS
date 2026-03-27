const logEl = document.getElementById('log');
const coursesEl = document.getElementById('courses');
const outputEl = document.getElementById('output-json');
const outputCourseSelect = document.getElementById('output-course-select');
const loadingOverlay = document.getElementById('loading-overlay');
const loadingText = document.getElementById('loading-text');
const toastEl = document.getElementById('toast');

let currentCourses = [];

function toast(message) {
  toastEl.textContent = message;
  toastEl.classList.remove('hidden');
  setTimeout(() => toastEl.classList.add('hidden'), 2400);
}

function setLoading(isLoading, text = 'Processing...') {
  loadingText.textContent = text;
  loadingOverlay.classList.toggle('hidden', !isLoading);
}

function log(msg, payload) {
  const line = `[${new Date().toLocaleTimeString()}] ${msg}`;
  logEl.textContent = `${line}\n${payload ? JSON.stringify(payload, null, 2) : ''}\n\n${logEl.textContent}`;
}

function setProgress(prefix, value, text) {
  document.getElementById(`${prefix}-progress`).value = value;
  document.getElementById(`${prefix}-progress-text`).textContent = text;
}

function downloadJson(url) {
  const link = document.createElement('a');
  link.href = url;
  link.click();
}

function populateKPIs(courses) {
  const lessonCount = courses.reduce((acc, c) => acc + c.lesson_count, 0);
  document.getElementById('kpi-courses').textContent = courses.length;
  document.getElementById('kpi-lessons').textContent = lessonCount;
  if (!courses.length) {
    document.getElementById('kpi-updated').textContent = '-';
    return;
  }
  const newest = [...courses].sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))[0];
  document.getElementById('kpi-updated').textContent = new Date(newest.updated_at).toLocaleString();
}

function populateOutputCourseSelect(courses) {
  outputCourseSelect.innerHTML = '';
  if (!courses.length) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'No courses available';
    outputCourseSelect.appendChild(option);
    return;
  }

  for (const course of courses) {
    const option = document.createElement('option');
    option.value = course.course_id;
    option.textContent = `${course.course_id} (${course.current_version})`;
    outputCourseSelect.appendChild(option);
  }
}

function renderCourses(courses) {
  if (!courses.length) {
    coursesEl.innerHTML = '<p>No courses uploaded yet.</p>';
    return;
  }
  const rows = courses.map(c => `
    <tr>
      <td>${c.course_id}</td>
      <td>${c.course_title}</td>
      <td>${c.current_version}</td>
      <td>${c.lesson_count}</td>
      <td>${new Date(c.updated_at).toLocaleString()}</td>
    </tr>`).join('');
  coursesEl.innerHTML = `<table><thead><tr><th>Course ID</th><th>Title</th><th>Version</th><th>Lessons</th><th>Updated</th></tr></thead><tbody>${rows}</tbody></table>`;
}

async function refreshCourses() {
  const res = await fetch('/courses');
  const data = await res.json();
  currentCourses = data.courses || [];
  populateOutputCourseSelect(currentCourses);
  populateKPIs(currentCourses);
  renderCourses(currentCourses);
}

function uploadWithProgress({ url, formData, prefix }) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url);

    setProgress(prefix, 0, 'Uploading... 0%');

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        setProgress(prefix, percent, `Uploading... ${percent}%`);
      } else {
        setProgress(prefix, 50, 'Uploading...');
      }
    };

    xhr.onload = () => {
      const data = xhr.responseText ? JSON.parse(xhr.responseText) : {};
      if (xhr.status >= 200 && xhr.status < 300) {
        setProgress(prefix, 100, 'Processing complete ✅');
        resolve(data);
      } else {
        setProgress(prefix, 0, 'Failed ❌');
        reject(data);
      }
    };

    xhr.onerror = () => {
      setProgress(prefix, 0, 'Failed ❌');
      reject({ detail: 'Network error' });
    };

    xhr.send(formData);
    setTimeout(() => {
      if (xhr.readyState !== 4) {
        setProgress(prefix, 100, 'Uploaded. Processing on server...');
      }
    }, 1200);
  });
}

async function loadCourseOutput() {
  const courseId = outputCourseSelect.value;
  if (!courseId) return;
  setLoading(true, `Loading output for ${courseId}...`);
  try {
    const res = await fetch(`/courses/${encodeURIComponent(courseId)}/latest`);
    const data = await res.json();
    outputEl.textContent = JSON.stringify(data, null, 2);
    log(`Loaded output JSON for ${courseId}`);
    toast(`Loaded ${courseId} output JSON`);
  } finally {
    setLoading(false);
  }
}

async function loadMasterOutput() {
  setLoading(true, 'Loading master output...');
  try {
    const res = await fetch('/master');
    const data = await res.json();
    outputEl.textContent = JSON.stringify(data, null, 2);
    log('Loaded master output JSON');
    toast('Loaded master output JSON');
  } finally {
    setLoading(false);
  }
}

document.getElementById('single-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const courseId = document.getElementById('single-course-id').value.trim();
  const file = document.getElementById('single-file').files[0];
  if (!courseId || !file) return;

  const fd = new FormData();
  fd.append('file', file);

  setLoading(true, `Processing ${courseId}...`);
  log(`Uploading ${file.name} for ${courseId}...`);
  try {
    const data = await uploadWithProgress({
      url: `/upload?course_id=${encodeURIComponent(courseId)}`,
      formData: fd,
      prefix: 'single',
    });
    log('Upload complete', data);
    await refreshCourses();
    outputCourseSelect.value = courseId;
    await loadCourseOutput();
    toast(`Upload complete for ${courseId}`);
  } catch (err) {
    log('Upload failed', err);
    toast('Single upload failed');
  } finally {
    setLoading(false);
  }
});

document.getElementById('bulk-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const ids = document.getElementById('bulk-course-ids').value.trim();
  const files = document.getElementById('bulk-files').files;
  if (!ids || !files.length) return;

  const fd = new FormData();
  for (const file of files) fd.append('files', file);

  setLoading(true, 'Processing bulk upload...');
  log(`Uploading batch (${files.length} files)...`);
  try {
    const data = await uploadWithProgress({
      url: `/upload/bulk?course_ids=${encodeURIComponent(ids)}`,
      formData: fd,
      prefix: 'bulk',
    });
    log('Bulk upload complete', data);
    await refreshCourses();
    await loadMasterOutput();
    toast('Bulk upload complete');
  } catch (err) {
    log('Bulk upload failed', err);
    toast('Bulk upload failed');
  } finally {
    setLoading(false);
  }
});

document.getElementById('refresh-courses').addEventListener('click', refreshCourses);
document.getElementById('load-course-output').addEventListener('click', loadCourseOutput);
document.getElementById('load-master-output').addEventListener('click', loadMasterOutput);
document.getElementById('download-course-output').addEventListener('click', () => {
  const courseId = outputCourseSelect.value;
  if (!courseId) return;
  downloadJson(`/courses/${encodeURIComponent(courseId)}/latest/download`);
});
document.getElementById('download-master-output').addEventListener('click', () => {
  downloadJson('/master/download');
});
document.getElementById('copy-output-json').addEventListener('click', async () => {
  await navigator.clipboard.writeText(outputEl.textContent || '');
  toast('Output JSON copied');
});
document.getElementById('course-filter').addEventListener('input', (e) => {
  const q = e.target.value.trim().toLowerCase();
  const filtered = currentCourses.filter(c =>
    c.course_id.toLowerCase().includes(q) || c.course_title.toLowerCase().includes(q)
  );
  renderCourses(filtered);
});

refreshCourses();
