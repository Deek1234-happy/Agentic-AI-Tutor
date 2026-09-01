# #  app/file_loader.py
# import os
# import tempfile
# import requests
# from urllib.parse import urlparse


# def download_if_url(file_path: str) -> str:
#     """
#     If file_path is a URL, download it and return a temporary local path.
#     Otherwise return the original path.
#     """

#     if file_path.startswith("http://") or file_path.startswith("https://"):

#         response = requests.get(file_path)

#         if response.status_code != 200:
#             raise FileNotFoundError("Could not download the file from URL")

#         # keep original extension
#         parsed = urlparse(file_path)
#         ext = os.path.splitext(parsed.path)[1]

#         temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)

#         temp_file.write(response.content)
#         temp_file.close()

#         return temp_file.name

#     return file_path

# app/file_loader.py

import logging
import os
import tempfile
import requests
import socket
import ipaddress
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Allowed document types
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".csv"}

# Maximum download size (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


def allow_internal_network() -> bool:
    """Opt-in bypass for local development only."""
    return os.getenv("ALLOW_INTERNAL_NETWORK", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def is_private_ip(hostname: str) -> bool:
    """
    Prevent SSRF attacks by blocking internal IPs.
    Allow loopback addresses for local development so the backend can fetch
    files from localhost without being blocked by the SSRF protection.
    """
    if hostname is None:
        return True

    normalized = hostname.strip().lower().strip("[]")
    if normalized in {"localhost", "127.0.0.1", "::1"}:
        return False

    try:
        ip = socket.gethostbyname(normalized)
        ip_obj = ipaddress.ip_address(ip)

        return (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_reserved
            or ip_obj.is_link_local
        )

    except Exception:
        return True


def download_if_url(file_path: str) -> str:
    """
    If file_path is a URL:
        - validate it
        - download it securely
        - store in temporary file
    Otherwise return the original path.
    """

    # ------------------------------------------------
    # Check if input is URL
    # ------------------------------------------------
    if file_path.startswith("http://") or file_path.startswith("https://"):

        parsed = urlparse(file_path)
        logger.info("[file_loader] Downloading URL: %s | host=%s | scheme=%s", file_path, parsed.hostname, parsed.scheme)

        # ------------------------------------------------
        # Validate scheme
        # ------------------------------------------------
        if parsed.scheme not in ["http", "https"]:
            logger.error("[file_loader] Invalid URL scheme: %s", file_path)
            raise ValueError("Invalid URL scheme")

        # ------------------------------------------------
        # Block internal network access (SSRF protection)
        # ------------------------------------------------
        if not allow_internal_network() and is_private_ip(parsed.hostname):
            logger.error("[file_loader] SSRF blocked: host=%s url=%s", parsed.hostname, file_path)
            raise ValueError("Access to internal network is blocked")

        # ------------------------------------------------
        # Validate file extension
        # ------------------------------------------------
        ext = os.path.splitext(parsed.path)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            logger.error("[file_loader] Disallowed file extension: %s from %s", ext, file_path)
            raise ValueError(f"File type not allowed: {ext}")

        # ------------------------------------------------
        # Download file with streaming
        # ------------------------------------------------
        try:
            response = requests.get(file_path, stream=True, timeout=10)
            logger.info("[file_loader] Received HTTP status %s for %s", response.status_code, file_path)

            if response.status_code != 200:
                raise FileNotFoundError("Could not download the file")

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)

            size = 0

            for chunk in response.iter_content(8192):

                if chunk:
                    size += len(chunk)

                    if size > MAX_FILE_SIZE:
                        temp_file.close()
                        os.remove(temp_file.name)
                        logger.error("[file_loader] Download exceeded max size: %s", file_path)
                        raise ValueError("File too large")

                    temp_file.write(chunk)

            temp_file.close()
            logger.info("[file_loader] Downloaded temp file: %s", temp_file.name)
            return temp_file.name

        except Exception:
            logger.exception("[file_loader] Failed to download file from URL: %s", file_path)
            raise

    logger.info("[file_loader] Using local file path directly: %s", file_path)

    # ------------------------------------------------
    # If local file
    # ------------------------------------------------
    return file_path