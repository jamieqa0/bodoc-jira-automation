import os
import sys
import io
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# 프로젝트 루트 경로 찾기
ROOT_DIR = Path(__file__).resolve().parent.parent

# .env 로드
load_dotenv(ROOT_DIR / ".env")

# Windows 한글 인코딩 자동 설정
if sys.platform == 'win32':
    # 출력 인코딩을 UTF-8로 강제 재설정
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding='utf-8')
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding='utf-8')
    # 터미널 코드페이지를 UTF-8로 변경 (명령어 실행 효과)
    os.system('chcp 65001 > nul')

class Settings:
    # Atlassian 공통
    ATLASSIAN_URL = os.getenv("ATLASSIAN_URL")
    ATLASSIAN_USER = os.getenv("ATLASSIAN_USER")
    ATLASSIAN_API_TOKEN = os.getenv("ATLASSIAN_API_TOKEN")

    # Jira/Confluence 상세 설정
    JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")
    CONFLUENCE_SPACE_KEY = os.getenv("CONFLUENCE_SPACE_KEY")
    CONFLUENCE_QA_REPORT_PARENT_ID = os.getenv("CONFLUENCE_QA_REPORT_PARENT_ID")
    CONFLUENCE_TEST_PLAN_PARENT_ID = os.getenv("CONFLUENCE_TEST_PLAN_PARENT_ID")
    CONFLUENCE_MOR_PARENT_ID = os.getenv("CONFLUENCE_MOR_PARENT_ID")

    # 경로 관련
    BASE_DIR = ROOT_DIR
    CORE_DIR = ROOT_DIR / "core"
    TEMPLATE_DIR = CORE_DIR / "templates"

    def get_current_date(self):
        """현재 날짜를 YYYY-MM-DD 형식으로 반환합니다."""
        return datetime.now().strftime('%Y-%m-%d')

    def validate(self):
        """필수 환경 변수가 설정되어 있는지 검증합니다."""
        required = {
            'ATLASSIAN_URL': self.ATLASSIAN_URL,
            'ATLASSIAN_USER': self.ATLASSIAN_USER,
            'ATLASSIAN_API_TOKEN': self.ATLASSIAN_API_TOKEN,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError(
                f".env 파일에 필수 환경 변수가 누락되었습니다: {', '.join(missing)}\n"
                f".env 파일 경로: {ROOT_DIR / '.env'}"
            )

settings = Settings()
settings.validate()
