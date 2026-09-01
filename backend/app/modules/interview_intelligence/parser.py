"""
Stage 1: Multi-Format Email Parser Engine
Extracts normalized email fields from .eml files, PDF emails, and plain text.
Extracts Message-ID, sender details, attachment metadata, clean body, and links.
Calculates SHA-256 hashes for deduplication and Cloudflare R2 storage keys.
"""

import email
import hashlib
import io
import re
from email import policy
from email.utils import parseaddr, parsedate_to_datetime
from typing import BinaryIO

from app.modules.interview_intelligence.schemas import NormalizedEmail

# Regex patterns for links and headers
URL_REGEX = re.compile(
    r"https?://[^\s<>\"'()]+",
    re.IGNORECASE,
)
EMAIL_HEADER_PATTERNS = {
    "from": re.compile(r"^(?:From|Sender):\s*(.+)$", re.IGNORECASE | re.MULTILINE),
    "subject": re.compile(r"^(?:Subject):\s*(.+)$", re.IGNORECASE | re.MULTILINE),
    "date": re.compile(r"^(?:Date|Sent):\s*(.+)$", re.IGNORECASE | re.MULTILINE),
    "to": re.compile(r"^(?:To):\s*(.+)$", re.IGNORECASE | re.MULTILINE),
    "message_id": re.compile(r"^(?:Message-ID|Message-Id):\s*<([^>]+)>", re.IGNORECASE | re.MULTILINE),
}


def compute_sha256(text: str) -> str:
    """Computes SHA-256 hex digest for a given text."""
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def compute_email_dedup_hash(subject: str, body: str, sender_email: str = "") -> str:
    """
    Computes a canonical SHA-256 hash across normalized subject + body + sender
    used for caching, R2 object naming, and database deduplication.
    """
    norm_subject = " ".join((subject or "").strip().lower().split())
    norm_body = " ".join((body or "").strip().lower().split())
    norm_sender = (sender_email or "").strip().lower()
    raw = f"{norm_subject}:::{norm_sender}:::{norm_body}"
    return compute_sha256(raw)


def extract_sender_info(raw_sender: str) -> tuple[str, str, str]:
    """
    Extracts (sender_name, sender_email, sender_domain) from a From header string.
    Example: "Sarah Johnson <sarah@amazon.com>" -> ("Sarah Johnson", "sarah@amazon.com", "amazon.com")
    """
    if not raw_sender:
        return "", "", ""

    clean_str = raw_sender.strip()
    name, addr = parseaddr(clean_str)

    if ("@" not in addr) and "@" in clean_str:
        # Fallback regex search for email in raw string
        match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", clean_str)
        if match:
            addr = match.group(0)
        name_cand = clean_str.split("<")[0].strip().strip("'\"")
        if name_cand and name_cand != addr:
            name = name_cand

    if not name and addr:
        name_candidate = clean_str.split("<")[0].strip().strip("'\"")
        if name_candidate and name_candidate != addr:
            name = name_candidate

    domain = ""
    if addr and "@" in addr:
        domain = addr.split("@")[-1].lower().strip()

    return name.strip(), addr.strip().lower(), domain


parse_sender_info = extract_sender_info


def clean_html_to_text(html_content: str) -> str:
    """Strips HTML tags, script/style tags, and normalizes whitespace."""
    if not html_content:
        return ""
    clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html_content, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<(br|/p|/div|/tr|/li)[^>]*>", "\n", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = clean.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    lines = [line.strip() for line in clean.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_links(text: str, html: str = "") -> list[str]:
    """Extracts unique URLs from text and HTML href attributes."""
    links: set[str] = set()

    if html:
        hrefs = re.findall(r'href=[\'"](https?://[^\'">\s]+)[\'"]', html, re.IGNORECASE)
        for h in hrefs:
            links.add(h.strip())

    if text:
        found = URL_REGEX.findall(text)
        for u in found:
            cleaned_u = u.rstrip(".,;)>]}")
            if cleaned_u.startswith("http"):
                links.add(cleaned_u)

    return sorted(list(links))


class EmailParser:
    """Multi-format recruiter email parser supporting .eml, PDF, and plain text."""

    @classmethod
    def parse_eml(cls, file_content: bytes | str) -> NormalizedEmail:
        """Parses an RFC 822 / MIME format .eml file."""
        if isinstance(file_content, str):
            msg = email.message_from_string(file_content, policy=policy.default)
        else:
            msg = email.message_from_bytes(file_content, policy=policy.default)

        subject = str(msg.get("Subject", "") or "").strip()
        from_hdr = str(msg.get("From", "") or "").strip()
        sender_name, sender_email, sender_domain = extract_sender_info(from_hdr)

        # Message-ID header
        message_id = None
        raw_msg_id = msg.get("Message-ID") or msg.get("Message-Id")
        if raw_msg_id:
            message_id = str(raw_msg_id).strip().strip("<>")

        # Date header
        received_time = None
        date_hdr = msg.get("Date")
        if date_hdr:
            try:
                received_time = parsedate_to_datetime(str(date_hdr))
            except Exception:
                pass

        body_parts = []
        html_parts = []
        attachments = []
        attachment_metadata = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get_content_disposition() or "")
                filename = part.get_filename()

                if filename:
                    attachments.append(filename)
                    payload_data = part.get_payload(decode=True)
                    size = len(payload_data) if payload_data else 0
                    attachment_metadata.append({
                        "name": filename,
                        "size": size,
                        "content_type": content_type,
                    })

                if disposition == "attachment":
                    continue

                if content_type == "text/plain":
                    try:
                        payload = part.get_content()
                        if isinstance(payload, str):
                            body_parts.append(payload)
                    except Exception:
                        pass
                elif content_type == "text/html":
                    try:
                        payload = part.get_content()
                        if isinstance(payload, str):
                            html_parts.append(payload)
                    except Exception:
                        pass
        else:
            content_type = msg.get_content_type()
            try:
                payload = msg.get_content()
                if isinstance(payload, str):
                    if content_type == "text/html":
                        html_parts.append(payload)
                    else:
                        body_parts.append(payload)
            except Exception:
                pass

        raw_html = "\n".join(html_parts)
        if body_parts:
            body = "\n".join(body_parts).strip()
        elif raw_html:
            body = clean_html_to_text(raw_html)
        else:
            body = ""

        links = extract_links(body, raw_html)
        body_sha256 = compute_sha256(body)
        email_hash = compute_email_dedup_hash(subject, body, sender_email)
        preview = body[:300].strip()

        return NormalizedEmail(
            message_id=message_id,
            subject=subject,
            sender_email=sender_email,
            sender_name=sender_name,
            sender_domain=sender_domain,
            body=body,
            body_preview=preview,
            body_sha256=body_sha256,
            links=links,
            attachment_names=attachments,
            attachment_metadata=attachment_metadata,
            received_time=received_time,
            email_hash=email_hash,
            source_format="eml",
            processing_status="parsed",
        )

    @classmethod
    def parse_pdf(cls, file_content: bytes | BinaryIO) -> NormalizedEmail:
        """Extracts text, metadata, and link annotations from PDF emails."""
        import pypdf

        if isinstance(file_content, bytes):
            stream = io.BytesIO(file_content)
        else:
            stream = file_content

        reader = pypdf.PdfReader(stream)
        extracted_pages = []
        links: set[str] = set()

        for page in reader.pages:
            text = page.extract_text() or ""
            extracted_pages.append(text)

            try:
                if "/Annots" in page:
                    for annot in page["/Annots"]:
                        annot_obj = annot.get_object()
                        if "/A" in annot_obj and "/URI" in annot_obj["/A"]:
                            uri = annot_obj["/A"]["/URI"]
                            if uri and uri.startswith("http"):
                                links.add(uri)
            except Exception:
                pass

        full_text = "\n".join(extracted_pages).strip()

        subject = ""
        sender_name = ""
        sender_email = ""
        sender_domain = ""
        received_time = None
        message_id = None

        meta = reader.metadata or {}
        if meta.title and not subject:
            subject = str(meta.title)
        if meta.creation_date:
            try:
                received_time = meta.creation_date
            except Exception:
                pass

        from_match = EMAIL_HEADER_PATTERNS["from"].search(full_text)
        if from_match:
            sender_name, sender_email, sender_domain = extract_sender_info(from_match.group(1))

        subj_match = EMAIL_HEADER_PATTERNS["subject"].search(full_text)
        if subj_match and not subject:
            subject = subj_match.group(1).strip()

        date_match = EMAIL_HEADER_PATTERNS["date"].search(full_text)
        if date_match and not received_time:
            try:
                received_time = parsedate_to_datetime(date_match.group(1).strip())
            except Exception:
                pass

        msg_id_match = EMAIL_HEADER_PATTERNS["message_id"].search(full_text)
        if msg_id_match:
            message_id = msg_id_match.group(1).strip()

        text_links = URL_REGEX.findall(full_text)
        for u in text_links:
            cleaned_u = u.rstrip(".,;)>]}")
            if cleaned_u.startswith("http"):
                links.add(cleaned_u)

        body_sha256 = compute_sha256(full_text)
        email_hash = compute_email_dedup_hash(subject, full_text, sender_email)
        preview = full_text[:300].strip()

        return NormalizedEmail(
            message_id=message_id,
            subject=subject,
            sender_email=sender_email,
            sender_name=sender_name,
            sender_domain=sender_domain,
            body=full_text,
            body_preview=preview,
            body_sha256=body_sha256,
            links=sorted(list(links)),
            attachment_names=[],
            attachment_metadata=[],
            received_time=received_time,
            email_hash=email_hash,
            source_format="pdf",
            processing_status="parsed",
        )

    @classmethod
    def parse_text(cls, text_content: str) -> NormalizedEmail:
        """Parses plain text / pasted email with regex header extraction and body separation."""
        raw_text = (text_content or "").strip()

        if "<html" in raw_text.lower() or "<body" in raw_text.lower() or "<div" in raw_text.lower():
            clean_body = clean_html_to_text(raw_text)
        else:
            clean_body = raw_text

        subject = ""
        sender_name = ""
        sender_email = ""
        sender_domain = ""
        received_time = None
        message_id = None

        from_match = EMAIL_HEADER_PATTERNS["from"].search(clean_body)
        if from_match:
            sender_name, sender_email, sender_domain = extract_sender_info(from_match.group(1))

        subj_match = EMAIL_HEADER_PATTERNS["subject"].search(clean_body)
        if subj_match:
            subject = subj_match.group(1).strip()

        date_match = EMAIL_HEADER_PATTERNS["date"].search(clean_body)
        if date_match:
            try:
                received_time = parsedate_to_datetime(date_match.group(1).strip())
            except Exception:
                pass

        msg_id_match = EMAIL_HEADER_PATTERNS["message_id"].search(clean_body)
        if msg_id_match:
            message_id = msg_id_match.group(1).strip()

        links = extract_links(clean_body)
        body_sha256 = compute_sha256(clean_body)
        email_hash = compute_email_dedup_hash(subject, clean_body, sender_email)
        preview = clean_body[:300].strip()

        return NormalizedEmail(
            message_id=message_id,
            subject=subject,
            sender_email=sender_email,
            sender_name=sender_name,
            sender_domain=sender_domain,
            body=clean_body,
            body_preview=preview,
            body_sha256=body_sha256,
            links=links,
            attachment_names=[],
            attachment_metadata=[],
            received_time=received_time,
            email_hash=email_hash,
            source_format="text",
            processing_status="parsed",
        )

    @classmethod
    def parse_any(
        cls,
        content: bytes | str,
        filename: str | None = None,
        mime_type: str | None = None,
    ) -> NormalizedEmail:
        """Auto-detects format from filename or content and routes to appropriate parser."""
        lower_name = (filename or "").lower()

        if lower_name.endswith(".eml") or (mime_type and "message/rfc822" in mime_type):
            return cls.parse_eml(content)

        if lower_name.endswith(".pdf") or (mime_type and "application/pdf" in mime_type):
            if isinstance(content, str):
                content = content.encode("utf-8", errors="ignore")
            return cls.parse_pdf(content)

        if isinstance(content, bytes):
            if content.startswith(b"%PDF"):
                return cls.parse_pdf(content)
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("latin-1", errors="ignore")
            return cls.parse_text(text)

        return cls.parse_text(content)
