'use strict';

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.report-form').forEach(function (form) {
    form.addEventListener('submit', handleSubmit);
  });
});

/**
 * Convert report_type string (underscores) to DOM id suffix (hyphens).
 * e.g. "test_plan" -> "test-plan"
 */
function toIdSuffix(reportType) {
  return reportType.replace(/_/g, '-');
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function clearFieldErrors(form) {
  form.querySelectorAll('.field-error').forEach(function (el) { el.remove(); });
  form.querySelectorAll('.input-invalid').forEach(function (el) {
    el.classList.remove('input-invalid');
  });
}

function showFieldError(input, message) {
  input.classList.add('input-invalid');
  var err = document.createElement('p');
  err.className = 'field-error';
  err.textContent = message;
  input.parentNode.appendChild(err);
}

function validateForm(form) {
  clearFieldErrors(form);
  var valid = true;
  var elements = form.elements;
  for (var i = 0; i < elements.length; i++) {
    var el = elements[i];
    if (!el.name || el.type === 'checkbox' || el.type === 'submit') continue;
    var val = el.value.trim();
    if (el.required && !val) {
      showFieldError(el, '필수 입력 항목입니다.');
      valid = false;
    } else if (el.type === 'email' && val && !isValidEmail(val)) {
      showFieldError(el, '올바른 이메일 형식이 아닙니다.');
      valid = false;
    }
  }
  return valid;
}

function handleSubmit(e) {
  e.preventDefault();

  var form = e.currentTarget;
  var reportType = form.dataset.reportType;

  if (!validateForm(form)) return;

  // Collect form data
  var formData = {};
  var elements = form.elements;
  for (var i = 0; i < elements.length; i++) {
    var el = elements[i];
    if (!el.name) continue;
    if (el.type === 'checkbox') {
      formData[el.name] = el.checked;
    } else if (el.value !== undefined) {
      formData[el.name] = el.value.trim();
    }
  }

  // Disable button and show running state
  var submitBtn = form.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  submitBtn.dataset.originalText = submitBtn.textContent;
  submitBtn.textContent = '실행 중...';

  // Clear previous output
  var suffix = toIdSuffix(reportType);
  var logArea = document.getElementById('log-' + suffix);
  var resultArea = document.getElementById('result-' + suffix);
  if (logArea) { logArea.textContent = ''; }
  if (resultArea) {
    resultArea.textContent = '';
    resultArea.className = 'result-area';
  }

  startReport(reportType, formData, form);
}

function startReport(reportType, data, form) {
  var payload = Object.assign({ report_type: reportType }, data);

  fetch('/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
    .then(function (res) {
      return res.json().then(function (body) {
        return { ok: res.ok, body: body };
      });
    })
    .then(function (result) {
      if (!result.ok) {
        var suffix = toIdSuffix(reportType);
        var resultArea = document.getElementById('result-' + suffix);
        showResult(
          { status: 'error', message: result.body.error || '알 수 없는 오류' },
          resultArea,
          form
        );
        if (result.body.redirect) {
          setTimeout(function () {
            window.location.href = result.body.redirect;
          }, 2000);
        }
        return;
      }
      streamLogs(result.body.job_id, reportType, form);
    })
    .catch(function (err) {
      var suffix = toIdSuffix(reportType);
      var resultArea = document.getElementById('result-' + suffix);
      showResult({ status: 'error', message: '요청 실패: ' + err.message }, resultArea, form);
    });
}

function streamLogs(jobId, reportType, form) {
  var suffix = toIdSuffix(reportType);
  var logArea = document.getElementById('log-' + suffix);
  var resultArea = document.getElementById('result-' + suffix);

  // Ensure log area is visible (non-empty triggers :not(:empty) CSS)
  if (logArea) { logArea.textContent = ' '; }

  var es = new EventSource('/stream/' + jobId);

  es.onmessage = function (e) {
    if (logArea) {
      logArea.textContent += e.data + '\n';
      logArea.scrollTop = logArea.scrollHeight;
    }
  };

  es.addEventListener('done', function (e) {
    es.close();
    var result;
    try {
      result = JSON.parse(e.data);
    } catch (_) {
      result = { status: 'error', message: '응답 파싱 실패' };
    }
    showResult(result, resultArea, form);
  });

  es.onerror = function () {
    es.close();
    showResult({ status: 'error', message: '연결 오류' }, resultArea, form);
  };
}

function showResult(result, resultArea, form) {
  // Re-enable submit button
  var submitBtn = form.querySelector('button[type="submit"]');
  submitBtn.disabled = false;
  submitBtn.textContent = submitBtn.dataset.originalText || '실행';

  if (!resultArea) return;

  if (result.status === 'success') {
    var url = result.url || '';
    if (url) {
      resultArea.innerHTML = '✅ 완료! <a href="' + url + '" target="_blank">Confluence 페이지 열기</a>';
    } else {
      resultArea.textContent = '✅ 완료!';
    }
    resultArea.className = 'result-area success';
  } else {
    resultArea.textContent = '❌ 오류: ' + (result.message || '알 수 없는 오류');
    resultArea.className = 'result-area error';
  }
}
