#!/usr/bin/env python3
"""
Ghost Blog & MySQL Integration Test Suite
=========================================
Validates:
1. Docker container status & MySQL database health (both main blog & poetry instances)
2. Ghost HTTP routing, theme asset rendering, and admin endpoint for kalp.dev
3. Absence of poetry content, routes, and links on kalp.dev
4. Subdomain HTTP routing, theme rendering, and poem delivery on poetry.kalp.dev
5. Backup pipeline integrity (MySQL dumps for both databases, content folders, configs)
6. Google Drive rclone integration
7. Systemd timer & service configurations
"""

import json
import os
import subprocess
import unittest
import urllib.error
import urllib.request

BASE_URL = os.environ.get("BLOG_BASE_URL", "http://127.0.0.1:2368")
POETRY_BASE_URL = os.environ.get("POETRY_BASE_URL", "http://127.0.0.1:2369")
HOST_HEADER = os.environ.get("BLOG_HOST_HEADER", "kalp.dev")
POETRY_HOST_HEADER = os.environ.get("POETRY_HOST_HEADER", "poetry.kalp.dev")
DB_CONTAINER = os.environ.get("DB_CONTAINER", "blog-db-1")
SERVER_CONTAINER = os.environ.get("SERVER_CONTAINER", "blog-ghost-1")
POETRY_SERVER_CONTAINER = os.environ.get("POETRY_SERVER_CONTAINER", "blog-ghost-poetry-1")


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevents automatic redirection so tests can inspect 301/302 responses."""
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        return None


def make_request(path, base_url=BASE_URL, host_header=HOST_HEADER, method="GET", headers=None, with_forwarded_proto=True, follow_redirects=True):
    url = f"{base_url}{path}"
    req_headers = {
        "User-Agent": "GhostBlogIntegrationTest/1.0",
        "Host": host_header,
    }
    if with_forwarded_proto:
        req_headers["X-Forwarded-Proto"] = "https"
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, headers=req_headers, method=method)
    handlers = [] if follow_redirects else [NoRedirectHandler()]
    opener = urllib.request.build_opener(*handlers)
    try:
        with opener.open(req, timeout=10) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except urllib.error.URLError as e:
        return 0, {}, str(e).encode("utf-8")


class TestDockerAndDatabaseHealth(unittest.TestCase):
    """Verifies Docker containers and MySQL database connectivity."""

    def test_docker_containers_running(self):
        """Ensure Ghost servers and MySQL database containers are Up."""
        res = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True, text=True, check=True
        )
        lines = res.stdout.strip().split("\n")
        containers = {line.split("\t")[0]: line.split("\t")[1] for line in lines if "\t" in line}

        self.assertIn(SERVER_CONTAINER, containers, f"{SERVER_CONTAINER} is not running")
        self.assertIn(POETRY_SERVER_CONTAINER, containers, f"{POETRY_SERVER_CONTAINER} is not running")
        self.assertIn(DB_CONTAINER, containers, f"{DB_CONTAINER} is not running")
        self.assertTrue(containers[SERVER_CONTAINER].startswith("Up"), f"{SERVER_CONTAINER} is down")
        self.assertTrue(containers[POETRY_SERVER_CONTAINER].startswith("Up"), f"{POETRY_SERVER_CONTAINER} is down")
        self.assertTrue(containers[DB_CONTAINER].startswith("Up"), f"{DB_CONTAINER} is down")

    def test_mysql_table_integrity_main_db(self):
        """Ensure critical Ghost MySQL database tables exist in ghost_db."""
        cmd = [
            "docker", "exec", DB_CONTAINER,
            "mysql", "-u", "ghost", "-pghostpassword", "-D", "ghost_db",
            "-N", "-e", "SELECT count(*) FROM posts; SELECT count(*) FROM users; SELECT count(*) FROM settings;"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        counts = [line.strip() for line in res.stdout.strip().split("\n") if line.strip().isdigit()]
        self.assertEqual(len(counts), 3, "Failed to query posts, users, and settings from MySQL ghost_db")
        post_count = int(counts[0])
        user_count = int(counts[1])
        settings_count = int(counts[2])

        self.assertGreater(user_count, 0, "No users found in ghost_db")
        self.assertGreater(post_count, 0, "No posts found in ghost_db")
        self.assertGreater(settings_count, 0, "No settings configured in ghost_db")

    def test_mysql_table_integrity_poetry_db(self):
        """Ensure critical Ghost MySQL database tables exist in ghost_poetry_db."""
        cmd = [
            "docker", "exec", DB_CONTAINER,
            "mysql", "-u", "ghost", "-pghostpassword", "-D", "ghost_poetry_db",
            "-N", "-e", "SELECT count(*) FROM posts; SELECT count(*) FROM users; SELECT count(*) FROM settings;"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        counts = [line.strip() for line in res.stdout.strip().split("\n") if line.strip().isdigit()]
        self.assertEqual(len(counts), 3, "Failed to query posts, users, and settings from MySQL ghost_poetry_db")
        post_count = int(counts[0])
        user_count = int(counts[1])
        settings_count = int(counts[2])

        self.assertGreater(user_count, 0, "No users found in ghost_poetry_db")
        self.assertGreater(post_count, 0, "No posts found in ghost_poetry_db")
        self.assertGreater(settings_count, 0, "No settings configured in ghost_poetry_db")


class TestGhostWebRoutingAndTheme(unittest.TestCase):
    """Tests Ghost frontend rendering, HTTPS redirection, and theme assets for kalp.dev."""

    def test_homepage_https_rendering(self):
        """Homepage with forwarded HTTPS header should return 200 OK with custom theme HTML."""
        status, headers, body = make_request("/", method="GET", with_forwarded_proto=True)
        self.assertEqual(status, 200)
        html = body.decode("utf-8")
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Kalp Shah", html)
        self.assertIn("Software Engineer &amp; Builder", html)
        self.assertIn("/assets/css/style.css", html)

    def test_homepage_no_poetry_leaks(self):
        """Homepage on kalp.dev must NOT contain any poetry links, cards, or mentions."""
        status, headers, body = make_request("/", method="GET", with_forwarded_proto=True)
        self.assertEqual(status, 200)
        html = body.decode("utf-8").lower()
        self.assertNotIn("poetry corner", html)
        self.assertNotIn("citylights and code", html)
        self.assertNotIn("digital echoes", html)
        self.assertNotIn('href="https://kalp.dev/poetry/"', html)
        self.assertNotIn('href="/poetry/"', html)

    def test_about_page_no_poetry_leaks(self):
        """About page on kalp.dev must NOT contain references to poetry."""
        status, headers, body = make_request("/about/", method="GET", with_forwarded_proto=True)
        self.assertEqual(status, 200)
        html = body.decode("utf-8").lower()
        self.assertNotIn("poetry", html)

    def test_poetry_route_returns_404_on_main_domain(self):
        """Request to /poetry/ on kalp.dev should return 404."""
        status, headers, body = make_request("/poetry/", method="GET", with_forwarded_proto=True)
        self.assertEqual(status, 404)

    def test_http_to_https_redirect(self):
        """Request without forwarded HTTPS header should return 301 redirect to canonical HTTPS."""
        status, headers, body = make_request("/", method="GET", with_forwarded_proto=False, follow_redirects=False)
        self.assertIn(status, (301, 302))
        location = headers.get("Location", headers.get("location", ""))
        self.assertTrue(location.startswith("https://kalp.dev"), f"Invalid redirect location: {location}")

    def test_theme_static_asset_serving(self):
        """Ghost should serve static theme assets (CSS/SVG) with 200 OK."""
        status, headers, body = make_request("/assets/css/style.css", method="GET", with_forwarded_proto=True)
        self.assertEqual(status, 200)
        self.assertGreater(len(body), 100, "Theme CSS asset is empty")

    def test_ghost_admin_endpoint(self):
        """Ghost admin endpoint /ghost/ should return 200 OK or redirect to sign-in."""
        status, headers, body = make_request("/ghost/", method="GET", with_forwarded_proto=True)
        self.assertIn(status, (200, 302))


class TestPoetrySubdomainRouting(unittest.TestCase):
    """Tests Ghost frontend rendering and poem serving on poetry.kalp.dev."""

    def test_poetry_homepage_rendering(self):
        """Homepage on poetry.kalp.dev should return 200 OK with poetry theme HTML."""
        status, headers, body = make_request(
            "/",
            base_url=POETRY_BASE_URL,
            host_header=POETRY_HOST_HEADER,
            method="GET",
            with_forwarded_proto=True
        )
        self.assertEqual(status, 200)
        html = body.decode("utf-8")
        self.assertIn("Poetry &amp; Verse", html)
        self.assertIn("Citylights and Code", html)
        self.assertIn("Digital Echoes", html)
        self.assertIn("kalp.dev", html)

    def test_poetry_individual_poem_rendering(self):
        """Single poem page on poetry.kalp.dev should return 200 OK and render verse."""
        status, headers, body = make_request(
            "/citylights-and-code/",
            base_url=POETRY_BASE_URL,
            host_header=POETRY_HOST_HEADER,
            method="GET",
            with_forwarded_proto=True
        )
        self.assertEqual(status, 200)
        html = body.decode("utf-8")
        self.assertIn("Citylights and Code", html)
        self.assertIn("hexadecimal", html)
        self.assertIn("poem-content", html)


class TestBackupAndStoragePipeline(unittest.TestCase):
    """Validates the blog backup & restore scripts, archive contents, and Google Drive upload."""

    def test_scripts_exist_and_executable(self):
        """Ensure backup.sh and restore.sh are present and executable."""
        for script in ["backup.sh", "restore.sh"]:
            path = f"/home/kalp/git/blog/scripts/{script}"
            self.assertTrue(os.path.isfile(path), f"{script} not found")
            self.assertTrue(os.access(path, os.X_OK), f"{script} is not executable")

    def test_local_backup_archive_integrity(self):
        """Ensure local backup archive exists and contains ghost_db.sql, content, and configs."""
        backup_dir = "/home/kalp/git/blog/backups"
        self.assertTrue(os.path.isdir(backup_dir), "backups directory missing")
        archives = [
            os.path.join(backup_dir, f)
            for f in os.listdir(backup_dir)
            if f.endswith(".tar.gz")
        ]
        self.assertGreater(len(archives), 0, "No local blog backup archives found")

        latest_archive = max(archives, key=os.path.getmtime)
        res = subprocess.run(["tar", "-tzf", latest_archive], capture_output=True, text=True, check=True)
        files = res.stdout.strip().split("\n")

        self.assertTrue(any("ghost_db.sql" in f for f in files), "ghost_db.sql missing from archive")
        self.assertTrue(any("content/" in f for f in files), "content/ directory missing from archive")
        self.assertTrue(any("docker-compose.yml" in f for f in files), "docker-compose.yml missing from archive")

    def test_rclone_gdrive_connectivity(self):
        """Ensure rclone can connect to Google Drive and list blog backups folder."""
        res = subprocess.run(
            ["rclone", "ls", "gdrive:blog backups"],
            capture_output=True, text=True, check=True
        )
        self.assertIn(".tar.gz", res.stdout, "No archives found in remote Google Drive blog backups")


class TestSystemdTimerIntegration(unittest.TestCase):
    """Validates that systemd units for blog backup are configured and active."""

    def test_backup_timer_active(self):
        """Ensure blog-backup.timer is active and scheduled in systemd."""
        res = subprocess.run(
            ["systemctl", "is-active", "blog-backup.timer"],
            capture_output=True, text=True
        )
        self.assertEqual(res.stdout.strip(), "active", "blog-backup.timer is not active")

    def test_backup_service_definition(self):
        """Ensure blog-backup.service points to the correct executable path."""
        res = subprocess.run(
            ["systemctl", "cat", "blog-backup.service"],
            capture_output=True, text=True, check=True
        )
        self.assertIn("ExecStart=/home/kalp/git/blog/scripts/backup.sh", res.stdout)


class TestMobileNavigation(unittest.TestCase):
    """Validates mobile navigation menu functionality, markup, and styles."""

    def test_kalp_dev_header_nav_markup(self):
        """Header partial must not have conflicting inline onclick and must have aria-expanded."""
        header_path = "/home/kalp/git/blog/content/themes/kalp-dev/partials/header.hbs"
        with open(header_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("onclick=", content, "Inline onclick handler found in header.hbs")
        self.assertIn('class="nav-toggle"', content)
        self.assertIn('aria-expanded="false"', content)
        self.assertIn('class="site-nav__menu"', content)

    def test_kalp_dev_main_js_logic(self):
        """main.js must contain robust mobile toggle, click-outside, and escape key handlers."""
        js_path = "/home/kalp/git/blog/content/themes/kalp-dev/assets/js/main.js"
        with open(js_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("nav-toggle", content)
        self.assertIn("classList.toggle('open')", content)
        self.assertIn("aria-expanded", content)
        self.assertIn("Escape", content)

    def test_kalp_dev_style_responsive_rules(self):
        """style.css must have responsive mobile navigation rules and animations."""
        css_path = "/home/kalp/git/blog/content/themes/kalp-dev/assets/css/style.css"
        with open(css_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn(".nav-toggle.open span:nth-child(1)", content)
        self.assertIn(".site-nav__links.open", content)
        self.assertIn(".site-nav__menu", content)
        self.assertIn("@media (max-width: 768px)", content)

    def test_poetry_theme_mobile_nav(self):
        """Poetry theme must also have mobile navigation toggle markup and styles."""
        header_path = "/home/kalp/git/blog/poetry-content/themes/poetry-theme/partials/header.hbs"
        with open(header_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("onclick=", content)
        self.assertIn('class="nav-toggle"', content)

        css_path = "/home/kalp/git/blog/poetry-content/themes/poetry-theme/assets/css/style.css"
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        self.assertIn(".site-nav__links.open", css_content)

    def test_rendered_homepage_contains_mobile_toggle(self):
        """Rendered homepage HTML must include the mobile navigation toggle and link to main.js."""
        status, headers, body = make_request(
            "/",
            base_url=BASE_URL,
            host_header=HOST_HEADER,
            method="GET",
            with_forwarded_proto=True
        )
        self.assertEqual(status, 200)
        html = body.decode("utf-8")
        self.assertIn('class="nav-toggle"', html)
        self.assertNotIn('onclick="document.querySelector', html)
        self.assertIn('assets/js/main.js', html)


class TestTextEncodingAndMojibake(unittest.TestCase):
    """Verifies that pages and database entries do not contain corrupted Mojibake characters."""

    def test_resume_page_character_encoding(self):
        """Resume page should render clean bullets and dashes without mojibake."""
        status, headers, body = make_request(
            "/resume/",
            base_url=BASE_URL,
            host_header=HOST_HEADER,
            method="GET",
            with_forwarded_proto=True
        )
        self.assertEqual(status, 200)
        html = body.decode("utf-8")
        # Assert absence of mojibake patterns
        for bad in ["â€¢", "â€”", "â€“", "Â·", "â†—"]:
            self.assertNotIn(bad, html, f"Found mojibake {bad} in resume page HTML")
        # Assert presence of expected clean characters
        self.assertIn("Java, Python, C#, JavaScript, React • AWS", html)
        self.assertIn("Software Engineer — Energy Toolbase", html)
        self.assertIn("Mar 2022 – Present", html)
        self.assertIn("GitHub</a> · <a", html)

    def test_about_page_character_encoding(self):
        """About page should render clean emoji without mojibake."""
        status, headers, body = make_request(
            "/about/",
            base_url=BASE_URL,
            host_header=HOST_HEADER,
            method="GET",
            with_forwarded_proto=True
        )
        self.assertEqual(status, 200)
        html = body.decode("utf-8")
        for bad in ["ðŸ‘‹", "ðŸ", "â€", "Â"]:
            self.assertNotIn(bad, html, f"Found mojibake {bad} in about page HTML")
        self.assertIn("Hey, I am Kalp. 👋", html)


if __name__ == "__main__":
    import warnings
    warnings.simplefilter("ignore", ResourceWarning)
    unittest.main(verbosity=2)

