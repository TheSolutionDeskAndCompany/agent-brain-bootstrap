import json, base64, requests
from agent.config.settings import WP_BASE_URL, WP_JWT_TOKEN, WP_USERNAME, WP_APP_PASSWORD
from agent.utils.logger import get_logger
log = get_logger("wp_client")

SESSION = requests.Session()

def _auth_headers():
    if WP_JWT_TOKEN:
        return {"Authorization": f"Bearer {WP_JWT_TOKEN}"}
    if WP_USERNAME and WP_APP_PASSWORD:
        token = base64.b64encode(f"{WP_USERNAME}:{WP_APP_PASSWORD}".encode()).decode()
        return {"Authorization": f"Basic {token}"}
    return {}

def get_latest_brain_post():
    url = f"{WP_BASE_URL}/wp-json/wp/v2/posts?per_page=1&_fields=id,title,acf"
    r = SESSION.get(url, headers=_auth_headers(), timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data:
        log.warning("No posts found with ACF (ok on first run).")
        return {"id": None, "title": None, "acf": {}}
    post = data[0]
    acf = post.get("acf", {})
    # Try to parse JSON strings
    for key in ("agent_personality", "agent_emotions"):
        if isinstance(acf.get(key), str):
            try:
                acf[key] = json.loads(acf[key])
            except Exception:
                pass
    return {"id": post.get("id"), "title": post.get("title"), "acf": acf}
