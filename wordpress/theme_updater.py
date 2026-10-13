import sys, os
sys.path.insert(0, os.path.abspath("."))
import requests
from bs4 import BeautifulSoup
from config import WP_SITE_URL, WP_USERNAME, WP_APP_PASSWORD


def get_authenticated_session():
    session = requests.Session()
    login_url = f"{WP_SITE_URL}/wp-login.php"
    resp = session.post(login_url, data={
        "log": WP_USERNAME,
        "pwd": WP_APP_PASSWORD,
        "rememberme": "forever",
        "wp-submit": "Log In"
    }, headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed: status {resp.status_code}")
    return session


def update_theme_file(session, filename, new_content):
    url = f"{WP_SITE_URL}/wp-admin/theme-editor.php?file={filename}&theme=blocksy-child"
    r = session.get(url)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch {filename}: status {r.status_code}")

    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.select_one("#template")
    if not form:
        raise RuntimeError(f"Form #template not found for {filename}")

    inputs = {inp.get("name"): inp.get("value") for inp in form.select("input") if inp.get("name")}
    post_data = {
        **inputs,
        "newcontent": new_content
    }

    save_resp = session.post(f"{WP_SITE_URL}/wp-admin/theme-editor.php", data=post_data)
    if save_resp.status_code != 200:
        raise RuntimeError(f"Failed to save {filename}: status {save_resp.status_code}")
    return True


if __name__ == "__main__":
    sess = get_authenticated_session()
    print("Logged in successfully.")
