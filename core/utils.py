import re
from datetime import datetime

# 이슈 해결 완료로 간주하는 상태 목록 (CLAUDE.md 비즈니스 규칙)
RESOLVED_STATUSES = frozenset([
    'Prod 배포완료','QA패스', 'Resolved', 'Closed', 'Done', 'Verified',
    '해결됨', '완료', '종료', '종료됨',
])

def extract_version(text):
    """
    텍스트에서 버전 정보를 추출합니다 (예: MAINTENANCE_4.9.1 QA -> 4.9.1)
    """
    version_match = re.search(r'(\d+\.\d+\.\d+)', text)
    return version_match.group(1) if version_match else "N/A"

def extract_project_name(text):
    """
    텍스트에서 프로젝트명을 추출합니다 (예: [보닥앱] MAINTENANCE_4.9.0 QA -> 보닥앱)
    """
    project_match = re.search(r'\[(.*?)\]', text)
    return project_match.group(1) if project_match else "Unknown"

def get_today_str():
    """오늘 날짜를 YYYY-MM-DD 형식으로 반환합니다."""
    return datetime.now().strftime("%Y-%m-%d")

def format_date(dt):
    """datetime 객체를 YYYY-MM-DD 형식의 문자열로 변환합니다."""
    # datetime-like object or pandas Timestamp
    try:
        if hasattr(dt, 'strftime'):
            return dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    return str(dt)
