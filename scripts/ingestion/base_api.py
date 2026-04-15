import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BaseAPIClient:
    def __init__(self, base_url: str, per_page: int = 100):
        self.base_url = base_url
        self.per_page = per_page

    def request(self, endpoint: str = "", params: dict = None) -> Optional[dict]:
        try:
            url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
            response = requests.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")

        return None