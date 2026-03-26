const logEl = document.getElementById('log');
const coursesEl = document.getElementById('courses');

function log(msg, payload) {
  const line = `[${new Date().toLocaleTimeString()}] ${msg}`;
  logEl.textContent = `${line}\n${payload ? JSON.stringify(payload, null, 2) : ''}\n\n${logEl.textContent}`;
}

async function refreshCourses() {
  const res = await fetch('/courses');
  const data = await res.json();
  if (!data.courses.length) {
    coursesEl.innerHTML = '<p>No courses uploaded yet.</p>';
    return;
  }
  const rows = data.courses.map(c => `
    <tr>
      <td>${c.course_id}</td>
      <td>${c.course_title}</td>
      <td>${c.current_version}</td>
      <td>${c.lesson_count}</td>
      <td>${new Date(c.updated_at).toLocaleString()}</td>
    </tr>`).join('');
  coursesEl.innerHTML = `<table><thead><tr><th>Course ID</th><th>Title</th><th>Version</th><th>Lessons</th><th>Updated</th></tr></thead><tbody>${rows}</tbody></table>`;
}

document.getElementById('single-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const courseId = document.getElementById('single-course-id').value.trim();
  const file = document.getElementById('single-file').files[0];
  if (!courseId || !file) return;

  const fd = new FormData();
  fd.append('file', file);

  log(`Uploading ${file.name} for ${courseId}...`);
  const res = await fetch(`/upload?course_id=${encodeURIComponent(courseId)}`, { method: 'POST', body: fd });
  const data = await res.json();
  if (!res.ok) {
    log('Upload failed', data);
    return;
  }
  log('Upload complete', data);
  refreshCourses();
});

document.getElementById('bulk-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const ids = document.getElementById('bulk-course-ids').value.trim();
  const files = document.getElementById('bulk-files').files;
  if (!ids || !files.length) return;

  const fd = new FormData();
  for (const file of files) fd.append('files', file);

  log(`Uploading batch (${files.length} files)...`);
  const res = await fetch(`/upload/bulk?course_ids=${encodeURIComponent(ids)}`, { method: 'POST', body: fd });
  const data = await res.json();
  if (!res.ok) {
    log('Bulk upload failed', data);
    return;
  }
  log('Bulk upload complete', data);
  refreshCourses();
});

document.getElementById('refresh-courses').addEventListener('click', refreshCourses);
refreshCourses();
