import json
import queue
import re
import threading
import uuid
import warnings
from datetime import date

from flask import Blueprint, Response, jsonify, render_template, request, stream_with_context

from config.ui_settings_loader import load_ui_settings

warnings.filterwarnings("ignore", message=".*Unverified HTTPS request.*")

reports_bp = Blueprint("reports", __name__)

# In-memory job store: job_id -> {status, log_queue, confluence_url, error}
_jobs: dict[str, dict] = {}

_REQUIRED_SETTINGS = ("atlassian_url", "atlassian_user", "atlassian_api_token", "confluence_space_key")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _patch_settings(url: str, user: str, token: str, space: str) -> dict:
    """Monkey-patch the global settings object and return originals for restore.

    Also temporarily sets os.environ so that config.settings can be imported
    without raising ValueError (validate() checks os.getenv at class-definition
    time, but the singleton is created once — subsequent imports reuse it).
    If the module is not yet imported, we pre-populate os.environ with the
    ui_settings values so validate() passes on first import.
    """
    import os

    orig_env = {
        "ATLASSIAN_URL": os.environ.get("ATLASSIAN_URL"),
        "ATLASSIAN_USER": os.environ.get("ATLASSIAN_USER"),
        "ATLASSIAN_API_TOKEN": os.environ.get("ATLASSIAN_API_TOKEN"),
        "CONFLUENCE_SPACE_KEY": os.environ.get("CONFLUENCE_SPACE_KEY"),
    }

    # Ensure env vars are set before importing settings (first-import guard)
    os.environ["ATLASSIAN_URL"] = url
    os.environ["ATLASSIAN_USER"] = user
    os.environ["ATLASSIAN_API_TOKEN"] = token
    os.environ["CONFLUENCE_SPACE_KEY"] = space

    from config import settings as settings_module  # noqa: PLC0415

    orig_attrs = {
        "ATLASSIAN_URL": settings_module.settings.ATLASSIAN_URL,
        "ATLASSIAN_USER": settings_module.settings.ATLASSIAN_USER,
        "ATLASSIAN_API_TOKEN": settings_module.settings.ATLASSIAN_API_TOKEN,
        "CONFLUENCE_SPACE_KEY": settings_module.settings.CONFLUENCE_SPACE_KEY,
    }
    settings_module.settings.ATLASSIAN_URL = url
    settings_module.settings.ATLASSIAN_USER = user
    settings_module.settings.ATLASSIAN_API_TOKEN = token
    settings_module.settings.CONFLUENCE_SPACE_KEY = space

    return {"attrs": orig_attrs, "env": orig_env}


def _restore_settings(orig: dict) -> None:
    import os
    from config import settings as settings_module  # noqa: PLC0415

    for key, val in orig["attrs"].items():
        setattr(settings_module.settings, key, val)

    # Restore (or remove) env vars
    for key, val in orig["env"].items():
        if val is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = val


def _make_log(job_id: str):
    """Return a log() helper that puts messages into the job queue."""
    def log(msg: str) -> None:
        try:
            _jobs[job_id]["log_queue"].put(msg)
        except Exception:
            pass
    return log


def _page_url(base_url: str, result: dict) -> str:
    """Derive a Confluence page URL from publish_page result."""
    if not result:
        return ""
    base = base_url.rstrip("/")
    if "_links" in result and "webui" in result.get("_links", {}):
        return f"{base}/wiki{result['_links']['webui']}"
    page_id = result.get("id", "")
    if page_id:
        return f"{base}/wiki/pages/viewpage.action?pageId={page_id}"
    return ""


# ── Background worker ─────────────────────────────────────────────────────────

# WARNING: _patch_settings()는 module-level 전역 singleton을 수정합니다.
# POST /run 요청이 동시에 들어오면 설정값이 서로 덮어씌워질 수 있습니다.
# 2인 팀의 로컬 환경에서는 허용 가능하지만, 동시 실행이 필요하다면
# generator 생성자에 credentials를 직접 전달하는 방식으로 리팩토링이 필요합니다.
def _run_report(job_id: str, params: dict, ui_settings: dict) -> None:
    log = _make_log(job_id)
    confluence_url = None

    url = ui_settings["atlassian_url"]
    user = ui_settings.get("atlassian_user") or params.get("user_email", "")
    token = ui_settings["atlassian_api_token"]
    space = ui_settings["confluence_space_key"]

    orig = _patch_settings(url, user, token, space)

    try:
        from core.clients.confluence import ConfluenceClient
        from core.clients.jira import JiraClient

        report_type = params.get("report_type")

        # ── Test Plan ───────────────────────────────────────────────────
        if report_type == "test_plan":
            task_key = params.get("task_key", "").strip()
            if not task_key:
                raise ValueError("태스크 키가 필요합니다.")

            log("Jira에서 이슈 정보 수집 중...")
            jira = JiraClient(url, user, token)
            confluence = ConfluenceClient(url, user, token)

            from core.generators.test_plan_generator import TestPlanGenerator
            generator = TestPlanGenerator(jira_client=jira, confluence_client=confluence)

            log("테스트 플랜 생성 중...")
            html, title = generator.generate(task_key)
            if not html:
                raise RuntimeError("테스트 플랜 생성에 실패했습니다.")

            log("Confluence에 게시 중...")
            result = confluence.publish_page(
                space=space,
                title=title,
                body=html,
                parent_id=params.get("parent_id") or ui_settings.get("test_plan_parent_id") or None,
                update=True,
            )
            if not result:
                raise RuntimeError("Confluence 게시에 실패했습니다.")

            confluence_url = _page_url(url, result)
            log(f"게시 완료: {confluence_url}")

        # ── QA Report ───────────────────────────────────────────────────
        elif report_type == "qa":
            task_key = params.get("task_key", "").strip()
            if not task_key:
                raise ValueError("태스크 키가 필요합니다.")

            log("Jira에서 결함 데이터 수집 중...")
            jira = JiraClient(url, user, token)
            confluence = ConfluenceClient(url, user, token)

            from core.generators.qa_report_generator import QAReportGenerator
            generator = QAReportGenerator(jira_client=jira)

            log("QA 보고서 생성 및 차트 렌더링 중...")
            result_data = generator.generate(task_key)
            if not result_data:
                raise RuntimeError("QA 보고서 생성에 실패했습니다.")

            html, charts, summary = result_data
            page_title = f"{summary} Report"

            log("Confluence에 게시 중...")
            page = confluence.publish_page(
                space=space,
                title=page_title,
                body=html,
                parent_id=params.get("parent_id") or ui_settings.get("qa_report_parent_id") or None,
                update=True,
            )
            if not page:
                raise RuntimeError("Confluence 게시에 실패했습니다.")

            page_id = page.get("id")
            if charts and page_id:
                log(f"차트 {len(charts)}개 첨부 중...")
                for name, data in charts.items():
                    confluence.attach_file(page_id, name, data)

            confluence_url = _page_url(url, page)
            log(f"게시 완료: {confluence_url}")

        # ── MOR Report ──────────────────────────────────────────────────
        elif report_type == "mor":
            month = params.get("month", "").strip()
            if not month:
                raise ValueError("대상 월이 필요합니다. (예: 2026-04)")

            user_email = params.get("user_email", user)
            confluence = ConfluenceClient(url, user, token)
            jira = JiraClient(url, user, token)

            log("사용자 정보 조회 중...")
            user_info = confluence.get_user_info(user_email)
            display_name = user_info.get("displayName", user_email.split("@")[0])

            log(f"Jira 데이터 수집 중... (사용자: {display_name}, 월: {month})")
            jira_issues = jira.fetch_user_issues(user_email, month, quiet=True)

            log("Confluence 데이터 수집 중...")
            confluence_pages = confluence.fetch_user_pages(user_email, month, quiet=True)

            log("MOR 초안 생성 중...")
            from core.generators.mor_report_generator import MorGenerator
            generator = MorGenerator()
            content = generator.generate_draft(jira_issues, confluence_pages, user_email, month)

            log("Confluence 형식으로 변환 중...")
            import markdown
            from jinja2 import Environment, FileSystemLoader
            from config import settings as settings_module

            html_content = markdown.markdown(content, extensions=["tables", "fenced_code"])
            env = Environment(loader=FileSystemLoader(str(settings_module.settings.TEMPLATE_DIR)))
            template = env.get_template("mor_report.html")
            page_title = f"MOR 초안 {month} - {display_name}"
            rendered_html = template.render(
                title=page_title,
                content=html_content,
                user=display_name,
                month=month,
                generated_date=settings_module.settings.get_current_date(),
            )

            log("Confluence에 게시 중...")
            result = confluence.publish_page(
                space=space,
                title=page_title,
                body=rendered_html,
                parent_id=params.get("parent_id") or ui_settings.get("mor_parent_id") or None,
            )
            if not result:
                raise RuntimeError("Confluence 게시에 실패했습니다.")

            confluence_url = _page_url(url, result)
            log(f"게시 완료: {confluence_url}")

        # ── Annual Report ───────────────────────────────────────────────
        elif report_type == "annual":
            from datetime import date as _date
            year_str = str(params.get("year", "")).strip()
            if not year_str:
                raise ValueError("대상 연도가 필요합니다.")
            year = int(year_str)
            if not (2020 <= year <= _date.today().year + 1):
                raise ValueError(f"연도는 2020~{_date.today().year + 1} 범위여야 합니다.")

            user_email = params.get("user_email", user)
            today = date.today()
            base_url_clean = url.rstrip("/")
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31" if year < today.year else today.strftime("%Y-%m-%d")
            is_current_year = year == today.year

            jira = JiraClient(url, user, token)
            confluence = ConfluenceClient(url, user, token)

            log(f"사용자 정보 조회 중... ({user_email})")
            user_info = confluence.get_user_info(user_email)
            user_info["email"] = user_email
            account_id = user_info["accountId"]
            if account_id == user_email:
                log("Confluence 사용자 조회 실패, Jira를 통해 accountId 재시도...")
                jira_id = jira.get_user_account_id(user_email)
                if jira_id:
                    account_id = jira_id
                    user_info["accountId"] = jira_id
                    log(f"  accountId 확인: {jira_id}")
                else:
                    log("  [경고] accountId 조회 실패 — Confluence 문서 수집이 0건일 수 있습니다.")

            log(f"Jira 이슈 수집 중... ({start_date} ~ {end_date})")
            jql_all = (
                f'((assignee = "{user_email}" OR reporter = "{user_email}") OR project = "SQA") '
                f'AND created >= "{start_date}" AND created <= "{end_date}" ORDER BY created ASC'
            )
            raw = jira.jira.search_issues(
                jql_all,
                maxResults=0,
                fields="key,summary,status,issuetype,priority,created,resolutiondate,project,fixVersions",
            )

            from core.utils import RESOLVED_STATUSES

            def _is_resolved(iss):
                return (
                    getattr(iss.fields, "resolutiondate", None) is not None
                    or iss.fields.status.name in RESOLVED_STATUSES
                )

            sqa_issues, defect_issues = [], []
            for iss in raw:
                raw_project_name = iss.fields.project.name
                project_key = iss.fields.project.key

                if project_key == "APTS":
                    versions = [v.name.lower() for v in getattr(iss.fields, "fixVersions", [])]
                    version_str = " ".join(versions)
                    summary_lower = iss.fields.summary.lower()
                    if (
                        "플래너" in version_str
                        or "planner" in version_str
                        or "플래너" in summary_lower
                        or "planner" in summary_lower
                    ):
                        project_name = "Planner & B2B"
                    elif (
                        "보닥" in version_str
                        or "bodoc" in version_str
                        or "보닥" in summary_lower
                        or "bodoc" in summary_lower
                    ):
                        project_name = "Bodoc 4.0"
                    else:
                        project_name = "Planner & B2B"
                elif project_key == "BODOCRUN":
                    project_name = "Bodoc 4.0"
                elif project_key in ("PLN3", "BDPLNPD"):
                    project_name = "Planner & B2B"
                else:
                    if "보닥" in raw_project_name or "Bodoc" in raw_project_name:
                        project_name = "Bodoc 4.0"
                    else:
                        project_name = "Planner & B2B"

                d = {
                    "key": iss.key,
                    "summary": iss.fields.summary,
                    "status": iss.fields.status.name,
                    "issuetype": iss.fields.issuetype.name,
                    "priority": iss.fields.priority.name if iss.fields.priority else "None",
                    "project_name": project_name,
                    "month": str(iss.fields.created)[:7],
                    "resolved": _is_resolved(iss),
                }
                if re.search(r"amplitude", iss.fields.summary, re.IGNORECASE):
                    d["amplitude"] = True
                (sqa_issues if project_key == "SQA" else defect_issues).append(d)

            log(f"  SQA(작업관리): {len(sqa_issues)}개 / 결함: {len(defect_issues)}개")

            log("Confluence 페이지 수집 중...")
            cql = (
                f'type = page AND space.type = "global" '
                f'AND (creator = "{account_id}" OR lastModifier = "{account_id}") '
                f'AND (created >= "{start_date}" OR lastModified >= "{start_date}") '
                f'AND (created <= "{end_date}" OR lastModified <= "{end_date}") '
                f'ORDER BY lastModified DESC'
            )
            pages = []
            for p in confluence.confluence.cql(cql, limit=100, expand="content.history").get("results", []):
                c = p.get("content", {})
                hist = c.get("history", {})
                pages.append({
                    "id": c.get("id", ""),
                    "title": c.get("title", ""),
                    "space": c.get("space", {}).get("name", ""),
                    "url": f"{base_url_clean}/wiki{c.get('_links', {}).get('webui', '')}",
                    "created": hist.get("createdDate", "")[:10],
                    "lastModified": (
                        hist.get("lastUpdated", {}).get("when", "")[:10]
                        if isinstance(hist.get("lastUpdated"), dict)
                        else ""
                    ),
                })
            log(f"  Confluence 페이지: {len(pages)}개")

            log("보고서 생성 중...")
            from core.generators.annual_report_generator import AnnualGenerator
            generator = AnnualGenerator()
            title, full_body = generator.generate_html(
                sqa_issues, defect_issues, pages, user_info, year, start_date, end_date, is_current_year
            )

            log(f"Confluence 게시 중: '{title}'")
            result = confluence.publish_page(
                space=space,
                title=title,
                body=full_body,
                parent_id=params.get("parent_id") or ui_settings.get("mor_parent_id") or None,
            )
            if not result:
                raise RuntimeError("Confluence 게시에 실패했습니다.")

            confluence_url = _page_url(url, result)
            log(f"게시 완료: {confluence_url}")

        else:
            raise ValueError(f"알 수 없는 report_type: {report_type}")

        _jobs[job_id]["confluence_url"] = confluence_url
        _jobs[job_id]["status"] = "done"

    except Exception as exc:
        _jobs[job_id]["error"] = str(exc)
        _jobs[job_id]["status"] = "error"
        log(f"[오류] {exc}")

    finally:
        _restore_settings(orig)
        # Sentinel — signals stream generator to stop
        try:
            _jobs[job_id]["log_queue"].put(None)
        except Exception:
            pass


# ── Routes ────────────────────────────────────────────────────────────────────

@reports_bp.route("/")
def index():
    settings = load_ui_settings()
    return render_template("index.html", settings=settings)


@reports_bp.route("/run", methods=["POST"])
def run_report():
    params = request.get_json(force=True, silent=True) or {}

    ui_settings = load_ui_settings()
    missing = [f for f in _REQUIRED_SETTINGS if not ui_settings.get(f)]
    if missing:
        return jsonify({"error": "설정을 먼저 입력해주세요.", "redirect": "/settings"}), 400

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "running",
        "log_queue": queue.Queue(),
        "confluence_url": None,
        "error": None,
    }

    t = threading.Thread(target=_run_report, args=(job_id, params, ui_settings), daemon=True)
    t.start()

    return jsonify({"job_id": job_id}), 200


@reports_bp.route("/stream/<job_id>")
def stream(job_id):
    if job_id not in _jobs:
        return Response("event: done\ndata: {\"status\": \"error\", \"message\": \"job not found\"}\n\n",
                        mimetype="text/event-stream")

    def generate():
        try:
            job = _jobs[job_id]
            q = job["log_queue"]

            while True:
                try:
                    item = q.get(timeout=30)
                except queue.Empty:
                    # Keep-alive comment to prevent proxy timeout
                    yield ": keep-alive\n\n"
                    continue

                if item is None:
                    # Sentinel received — job finished
                    if job["error"]:
                        payload = json.dumps({"status": "error", "message": job["error"]}, ensure_ascii=False)
                    else:
                        payload = json.dumps({"status": "success", "url": job.get("confluence_url", "")}, ensure_ascii=False)
                    yield f"event: done\ndata: {payload}\n\n"
                    _jobs.pop(job_id, None)   # 완료된 job 메모리 해제
                    break

                # Regular log line
                yield f"data: {item}\n\n"
        except Exception as exc:
            payload = json.dumps({"status": "error", "message": f"스트림 오류: {exc}"}, ensure_ascii=False)
            yield f"event: done\ndata: {payload}\n\n"
            _jobs.pop(job_id, None)

    response = Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response
