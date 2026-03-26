const logEl = document.getElementById('log');
const coursesEl = document.getElementById('courses');

function log(msg, payload) {
  const line = `[${new Date().toLocaleTimeString()}] ${msg}`;
  logEl.textContent = `${line}\n${payload ? JSON.stringify(payload, null, 2) : ''}\n\n${logEl.textContent}`;
}

function setProgress(prefix, value, text) {
  document.getElementById(`${prefix}-progress`).value = value;
  document.getElementById(`${prefix}-progress-text`).textContent = text;
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

document.getElementById('single-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const courseId = document.getElementById('single-course-id').value.trim();
  const file = document.getElementById('single-file').files[0];
  if (!courseId || !file) return;

  const fd = new FormData();
  fd.append('file', file);

  log(`Uploading ${file.name} for ${courseId}...`);
  try {
    const data = await uploadWithProgress({
      url: `/upload?course_id=${encodeURIComponent(courseId)}`,
      formData: fd,
      prefix: 'single',
    });
    log('Upload complete', data);
    refreshCourses();
  } catch (err) {
    log('Upload failed', err);
  }
});

document.getElementById('bulk-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const ids = document.getElementById('bulk-course-ids').value.trim();
  const files = document.getElementById('bulk-files').files;
  if (!ids || !files.length) return;

  const fd = new FormData();
  for (const file of files) fd.append('files', file);

  log(`Uploading batch (${files.length} files)...`);
  try {
    const data = await uploadWithProgress({
      url: `/upload/bulk?course_ids=${encodeURIComponent(ids)}`,
      formData: fd,
      prefix: 'bulk',
    });
    log('Bulk upload complete', data);
    refreshCourses();
  } catch (err) {
    log('Bulk upload failed', err);
  }
});

document.getElementById('refresh-courses').addEventListener('click', refreshCourses);
refreshCourses();
