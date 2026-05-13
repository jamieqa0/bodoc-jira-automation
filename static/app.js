'use strict';

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.report-form').forEach(function (form) {
    form.addEventListener('submit', handleSubmit);
  });

  initSidebar();
});

function initSidebar() {
  var navItems = document.querySelectorAll('.js-nav-item');
  if (!navItems.length) return;

  // 첫 번째 섹션 기본 활성화
  activateSection('test-plan');

  navItems.forEach(function (item) {
    item.addEventListener('click', function (e) {
      var section = item.dataset.section;
      if (!section) return;
      // 현재 페이지가 index가 아니면 홈으로 이동
      if (!document.getElementById('section-' + section)) return;
      e.preventDefault();
      activateSection(section);
    });
  });
}

function activateSection(sectionId) {
  // 모든 섹션 숨기기
  document.querySelectorAll('.report-section').forEach(function (s) {
    s.classList.remove('is-active');
  });
  // 모든 nav 항목 비활성화
  document.querySelectorAll('.js-nav-item').forEach(function (n) {
    n.classList.remove('is-active');
  });

  // 대상 섹션 표시
  var target = document.getElementById('section-' + sectionId);
  if (target) target.classList.add('is-active');

  // 대상 nav 항목 활성화
  var navItem = document.querySelector('.js-nav-item[data-section="' + sectionId + '"]');
  if (navItem) navItem.classList.add('is-active');
}

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
  form.querySelectorAll('.field-error, .field-warning').forEach(function (el) { el.remove(); });
  form.querySelectorAll('.input-invalid, .input-warning').forEach(function (el) {
    el.classList.remove('input-invalid', 'input-warning');
  });
}

function showFieldError(input, message) {
  input.classList.add('input-invalid');
  var err = document.createElement('p');
  err.className = 'field-error';
  err.textContent = message;
  input.parentNode.appendChild(err);
}

function showFieldWarning(input, message) {
  input.classList.add('input-warning');
  var warn = document.createElement('p');
  warn.className = 'field-warning';
  warn.textContent = '⚠ ' + message;
  input.parentNode.appendChild(warn);
}

function isFutureMonth(value) {
  var match = value.match(/^(\d{4})-(\d{2})$/);
  if (!match) return false;
  var now = new Date();
  var inputYear = parseInt(match[1], 10);
  var inputMonth = parseInt(match[2], 10);
  return inputYear > now.getFullYear() ||
    (inputYear === now.getFullYear() && inputMonth > now.getMonth() + 1);
}

function isFutureYear(value) {
  return parseInt(value, 10) > new Date().getFullYear();
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
    } else if (el.name === 'month' && val && isFutureMonth(val)) {
      showFieldWarning(el, '아직 지나지 않은 월입니다. 데이터가 없을 수 있습니다.');
    } else if (el.name === 'year' && val && isFutureYear(val)) {
      showFieldWarning(el, '아직 지나지 않은 연도입니다. 데이터가 없을 수 있습니다.');
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

function getFormSnapshot(form) {
  var data = {};
  var elements = form.elements;
  for (var i = 0; i < elements.length; i++) {
    var el = elements[i];
    if (!el.name) continue;
    if (el.type === 'checkbox') {
      data[el.name] = el.checked;
    } else if (el.value !== undefined) {
      data[el.name] = el.value.trim();
    }
  }
  return data;
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
          resultArea, form, reportType, data
        );
        if (result.body.redirect) {
          setTimeout(function () {
            window.location.href = result.body.redirect;
          }, 2000);
        }
        return;
      }
      streamLogs(result.body.job_id, reportType, form, data);
    })
    .catch(function (err) {
      var suffix = toIdSuffix(reportType);
      var resultArea = document.getElementById('result-' + suffix);
      showResult({ status: 'error', message: '요청 실패: ' + err.message }, resultArea, form, reportType, data);
    });
}

function streamLogs(jobId, reportType, form, formData) {
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
    showResult(result, resultArea, form, reportType, formData);
  });

  es.onerror = function () {
    es.close();
    showResult({ status: 'error', message: '연결 오류' }, resultArea, form, reportType, formData);
  };
}

function showResult(result, resultArea, form, reportType, formData) {
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
    var msg = '❌ 오류: ' + (result.message || '알 수 없는 오류');
    resultArea.className = 'result-area error';

    if (reportType && formData) {
      var retryBtn = document.createElement('button');
      retryBtn.type = 'button';
      retryBtn.className = 'btn-retry';
      retryBtn.textContent = '재시도';
      retryBtn.addEventListener('click', function () {
        resultArea.textContent = '';
        resultArea.className = 'result-area';
        var suffix = toIdSuffix(reportType);
        var logArea = document.getElementById('log-' + suffix);
        if (logArea) logArea.textContent = '';

        submitBtn.disabled = true;
        submitBtn.dataset.originalText = submitBtn.textContent;
        submitBtn.textContent = '실행 중...';

        startReport(reportType, formData, form);
      });

      resultArea.textContent = msg;
      resultArea.appendChild(document.createElement('br'));
      resultArea.appendChild(retryBtn);
    } else {
      resultArea.textContent = msg;
    }
  }
}
