import calendar
import logging
import io
import re
from atlassian import Confluence

class ConfluenceClient:
    def __init__(self, url, user, token):
        self.url = url.rstrip('/')
        self.user = user
        self.token = token
        try:
            self.confluence = Confluence(
                url=self.url,
                username=self.user,
                password=self.token,
                verify_ssl=False
            )
            logging.info("Confluence 연결 성공")
        except Exception as e:
            logging.error(f"Confluence 연결 실패: {e}")
            raise

    def _find_trashed_page_id(self, space, title):
        """휴지통에 있는 페이지 ID를 검색합니다."""
        try:
            results = self.confluence.get(
                "rest/api/content",
                params={"title": title, "spaceKey": space, "type": "page", "status": "trashed"}
            )
            for item in (results.get('results', []) if isinstance(results, dict) else []):
                if item.get('title', '').strip() == title.strip():
                    return item.get('id')
        except Exception as e:
            logging.debug(f"휴지통 페이지 검색 실패: {e}")
        return None

    def _restore_and_update_page(self, page_id, title, body, parent_id):
        """휴지통 페이지를 복구하면서 내용을 업데이트합니다."""
        try:
            version = self.confluence.history(page_id)["lastUpdated"]["number"] + 1
            data = {
                "id": page_id,
                "type": "page",
                "title": title,
                "status": "current",
                "version": {"number": version},
                "metadata": {"properties": {
                    "content-appearance-draft": {"value": "full-width"},
                    "content-appearance-published": {"value": "full-width"},
                }},
                "body": {"storage": {"value": body, "representation": "storage"}},
            }
            if parent_id:
                data["ancestors"] = [{"type": "page", "id": parent_id}]
            result = self.confluence.put(f"rest/api/content/{page_id}", data=data)
            logging.info(f"휴지통에서 복구 후 업데이트: {title} ({page_id})")
            return result
        except Exception as e:
            logging.error(f"휴지통 페이지 복구 실패: {e}")
            return None

    def _find_page_id_by_cql(self, space, title):
        """CQL로 페이지 ID를 검색합니다. 특수문자 대비 포함 검색 후 Python에서 정확 매칭."""
        title_stripped = title.strip()
        # 첫 15자를 키워드로 포함 검색 (대괄호·콜론 등 CQL 특수문자 회피)
        keyword = title_stripped[:15].replace('"', '').replace('\\', '')
        try:
            cql = f'type = page AND space = "{space}" AND title ~ "{keyword}"'
            res = self.confluence.cql(cql, limit=50)
            for item in res.get('results', []):
                content = item.get('content', {})
                if content.get('title', '').strip() == title_stripped:
                    return content.get('id')
        except Exception as e:
            logging.warning(f"CQL 페이지 검색 실패: {e}")
        return None

    def publish_page(self, space, title, body, parent_id=None, update=True, quiet=False):
        """Confluence에 페이지를 생성하거나 업데이트합니다."""
        try:
            # 기존 페이지 확인: get_page_id → CQL 순으로 시도
            page_id = self.confluence.get_page_id(space, title)
            logging.info(f"get_page_id 결과: {page_id!r} (title={title!r})")
            if not page_id:
                page_id = self._find_page_id_by_cql(space, title)
                logging.info(f"CQL fallback 결과: {page_id!r}")

            if page_id:
                if update:
                    logging.info(f"기존 페이지 업데이트: {title} ({page_id})")
                    result = self.confluence.update_page(page_id, title, body, parent_id=parent_id, full_width=True)
                else:
                    logging.info(f"페이지가 이미 존재하며 업데이트 모드가 아님: {title}")
                    return {"id": page_id}
            else:
                logging.info(f"새 페이지 생성: {title}")
                try:
                    result = self.confluence.create_page(space, title, body, parent_id=parent_id, full_width=True)
                except Exception as create_err:
                    logging.warning(f"create_page 실패: {create_err}")
                    # 1순위: 살아있는 중복 페이지 탐색
                    page_id = self._find_page_id_by_cql(space, title)
                    if page_id and update:
                        logging.info(f"중복 감지, CQL로 찾아 업데이트: {title} ({page_id})")
                        result = self.confluence.update_page(page_id, title, body, parent_id=parent_id, full_width=True)
                    else:
                        # 2순위: 휴지통 페이지 탐색 후 복구
                        trashed_id = self._find_trashed_page_id(space, title)
                        if trashed_id and update:
                            logging.info(f"휴지통 페이지 감지, 복구 후 업데이트: {title} ({trashed_id})")
                            result = self._restore_and_update_page(trashed_id, title, body, parent_id)
                        else:
                            raise

            # 반환값 정규화: 항상 dict with 'id' 키를 보장
            if isinstance(result, dict) and 'id' in result:
                return result
            elif isinstance(result, dict) and 'content' in result:
                return {"id": result['content'].get('id')}
            elif page_id:
                return {"id": str(page_id)}
            return result
        except Exception as e:
            import traceback
            logging.error(f"Confluence 페이지 게시 실패: {e}")
            # ApiValueError wraps the original HTTPError in e.reason
            reason = getattr(e, 'reason', None)
            if reason is not None:
                resp = getattr(reason, 'response', None)
                if resp is not None:
                    logging.error(f"Confluence API 실제 응답 ({resp.status_code}): {resp.text}")
            logging.error(traceback.format_exc())
            return None

    def attach_file(self, page_id, filename, file_data, content_type='image/png'):
        """페이지에 파일을 첨부합니다."""
        try:
            # BytesIO인 경우 값 추출
            if isinstance(file_data, io.BytesIO):
                file_data = file_data.getvalue()
            
            return self.confluence.attach_content(
                file_data,
                name=filename,
                content_type=content_type,
                page_id=page_id,
                space=None  # page_id가 있으면 필요 없음
            )
        except Exception as e:
            logging.error(f"파일 첨부 실패 ({filename}): {e}")
            return None

    def get_user_info(self, user_email):
        """이메일로 accountId와 displayName을 조회합니다."""
        try:
            result = self.confluence.get("rest/api/user/current")
            if isinstance(result, dict) and result.get('email', '').lower() == user_email.lower():
                return {
                    'accountId': result.get('accountId', user_email),
                    'displayName': result.get('displayName', user_email),
                }
            # Atlassian Cloud는 list 또는 {"results": [...]} 형태 모두 반환 가능
            results = self.confluence.get(f"rest/api/user/search?query={user_email}")
            user_list = (
                results if isinstance(results, list)
                else results.get('results', []) if isinstance(results, dict)
                else []
            )
            if user_list:
                return {
                    'accountId': user_list[0].get('accountId', user_email),
                    'displayName': user_list[0].get('displayName', user_email),
                }
        except Exception as e:
            logging.warning(f"사용자 정보 조회 실패, email로 대체: {e}")
        logging.warning(f"accountId 조회 실패 — CQL이 0건 반환될 수 있음: {user_email}")
        return {'accountId': user_email, 'displayName': user_email}

    def _get_account_id(self, user_email):
        """이메일로 Confluence accountId를 조회합니다. 실패 시 이메일 그대로 반환."""
        return self.get_user_info(user_email)['accountId']

    def fetch_user_pages(self, user_email, year_month, quiet=False):
        """지정한 월에 사용자가 생성하거나 마지막으로 수정한 페이지를 가져옵니다."""
        year, month = map(int, year_month.split('-'))
        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year_month}-01"
        end_date = f"{year_month}-{last_day:02d}"

        # Atlassian Cloud CQL은 이메일 대신 accountId를 요구함
        account_id = self._get_account_id(user_email)

        # CQL 쿼리: creator 또는 lastModifier가 user이고, created 또는 lastModified가 해당 월
        cql = (
            f'type = page AND (creator = "{account_id}" OR lastModifier = "{account_id}") '
            f'AND space.type = "global" '
            f'AND (created >= "{start_date}" OR lastModified >= "{start_date}") '
            f'AND (created <= "{end_date}" OR lastModified <= "{end_date}") '
            'ORDER BY lastModified DESC'
        )

        try:
            # Confluence CQL 검색 (content.history 확장 포함하여 날짜 정보 가져옴)
            response = self.confluence.cql(cql, limit=100, expand='content.history')
            pages = response.get('results', [])

            result = []
            for page in pages:
                c = page.get('content', {})
                hist = c.get('history', {})
                last_mod = hist.get('lastModified', {})

                page_id = c.get('id', '')
                excerpt = ""
                try:
                    full = self.confluence.get_page_by_id(page_id, expand='body.storage')
                    body_html = full['body']['storage']['value']
                    clean_text = re.sub(r'<[^>]+>', '', body_html)
                    excerpt = clean_text[:300] + "..." if len(clean_text) > 300 else clean_text
                except Exception as e:
                    logging.debug(f"본문 로드 실패 (page_id={page_id}): {e}")
                    excerpt = "본문 로드 실패"

                result.append({
                    'title': c.get('title', ''),
                    'space': c.get('space', {}).get('name', ''),
                    'created': hist.get('createdDate', '')[:10],
                    'lastModified': hist.get('lastUpdated', {}).get('when', '')[:10] if isinstance(hist.get('lastUpdated'), dict) else '',
                    'url': f"{self.url}/wiki{c.get('_links', {}).get('webui', '')}",
                    'excerpt': excerpt
                })

            logging.info(f"{year_month} {user_email} 페이지 {len(result)}개 조회 완료")
            return result
        except Exception as e:
            logging.error(f"fetch_user_pages 실패: {e}")
            return []
