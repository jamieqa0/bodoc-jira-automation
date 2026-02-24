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

    def publish_page(self, space, title, body, parent_id=None, update=True):
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
