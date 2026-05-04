from atlassian import Confluence
import logging
import io

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

    def publish_page(self, space, title, body, parent_id=None, update=True, quiet=False):
        """Confluence에 페이지를 생성하거나 업데이트합니다."""
        try:
            # 기존 페이지 확인
            page_id = self.confluence.get_page_id(space, title)
            
            if page_id:
                if update:
                    logging.info(f"기존 페이지 업데이트: {title} ({page_id})")
                    result = self.confluence.update_page(page_id, title, body, parent_id=parent_id)
                else:
                    logging.info(f"페이지가 이미 존재하며 업데이트 모드가 아님: {title}")
                    return {"id": page_id}
            else:
                logging.info(f"새 페이지 생성: {title}")
                result = self.confluence.create_page(space, title, body, parent_id=parent_id)

            # 반환값 정규화: 항상 dict with 'id' 키를 보장
            if isinstance(result, dict) and 'id' in result:
                return result
            elif isinstance(result, dict) and 'content' in result:
                return {"id": result['content'].get('id')}
            elif page_id:
                return {"id": str(page_id)}
            return result
        except Exception as e:
            logging.error(f"Confluence 페이지 게시 실패: {e}")
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

    def fetch_user_pages(self, user_email, year_month, quiet=False):
        """지정한 월에 사용자가 생성하거나 마지막으로 수정한 페이지를 가져옵니다."""
        import calendar
        year, month = map(int, year_month.split('-'))
        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year_month}-01"
        end_date = f"{year_month}-{last_day:02d}"

        # CQL 쿼리: creator 또는 lastModifier가 user이고, created 또는 lastModified가 해당 월
        cql = (
            f'(creator = "{user_email}" OR lastModifier = "{user_email}") '
            f'AND (created >= "{start_date}" OR lastModified >= "{start_date}") '
            f'AND (created <= "{end_date}" OR lastModified <= "{end_date}") '
            'ORDER BY lastModified DESC'
        )

        try:
            # Confluence CQL 검색
            response = self.confluence.cql(cql, limit=50)  # 최대 50개
            pages = response.get('results', [])

            result = []
            for page in pages:
                # 본문 excerpt 가져오기 (선택적)
                excerpt = ""
                try:
                    content = self.confluence.get_page_by_id(page['content']['id'], expand='body.storage')
                    body_html = content['body']['storage']['value']
                    # 간단한 excerpt (HTML 태그 제거 후 300자)
                    import re
                    clean_text = re.sub(r'<[^>]+>', '', body_html)
                    excerpt = clean_text[:300] + "..." if len(clean_text) > 300 else clean_text
                except:
                    excerpt = "본문 로드 실패"

                result.append({
                    'title': page['content']['title'],
                    'space': page['content']['space']['name'],
                    'created': page['content']['history']['createdDate'][:10],
                    'lastModified': page['content']['history']['lastModified']['when'][:10],
                    'url': f"{self.url}{page['content']['_links']['webui']}",
                    'excerpt': excerpt
                })

            logging.info(f"{year_month} {user_email} 페이지 {len(result)}개 조회 완료")
            return result
        except Exception as e:
            logging.error(f"fetch_user_pages 실패: {e}")
            return []
