import logging
import requests

logger = logging.getLogger(__name__)


def get_access_token(client_id: str, client_secret: str) -> str:
    """
    Authenticates with the Reddit API to get an access token.
    """
    auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
    data = {
        "grant_type": "client_credentials",
    }
    headers = {"User-Agent": "RedditMarkdownConverter/1.0 (Safe Download Bot)"}

    try:
        res = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=auth,
            data=data,
            headers=headers,
            timeout=10,
        )
        res.raise_for_status()  # Raise an exception for bad status codes
        token = res.json().get("access_token", "")
        if not token:
            logger.error("Failed to retrieve access token. Response: %s", res.json())
            return ""
        logger.info("Successfully authenticated with Reddit.")
        return token
    except requests.exceptions.RequestException as e:
        logger.error(f"Error authenticating with Reddit: {e}")
        return ""
