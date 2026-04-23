"""
Threat detection engine for Magma Bitcoin app.
Analyzes request patterns, user-agent strings, and IP addresses to
identify and block malicious actors.
Pure Python stdlib — no third-party dependencies.
"""

import re
import time
import threading
import ipaddress
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Known malicious / suspicious patterns
# ---------------------------------------------------------------------------

_BOT_UA_PATTERNS = re.compile(
    r"(sqlmap|nikto|nmap|masscan|zgrab|dirbuster|gobuster|wfuzz|hydra"
    r"|medusa|burpsuite|acunetix|nessus|openvas|metasploit|msfconsole"
    r"|python-requests/[012]\.|go-http-client|libwww-perl|curl/[67]"
    r"|wget/|scrapy|phantomjs|headlessChrome|selenium|puppeteer"
    r"|arachni|skipfish|w3af|paros|webscarab|vega|appscan"
    r"|java/[01]\.|okhttp|axios/0\.[0-9]\.|python-urllib)",
    re.IGNORECASE,
)

_SCANNER_PATH_PATTERNS = re.compile(
    r"(/etc/passwd|/etc/shadow|/proc/self|/wp-admin|/wp-login"
    r"|/phpmyadmin|/pma|/admin\.php|/config\.php|/\.env|/\.git"
    r"|/\.svn|/\.htaccess|/backup|/dump\.sql|/database\.sql"
    r"|/shell\.php|/cmd\.php|/eval\.php|/webshell|/c99\.php"
    r"|/r57\.php|/upload\.php|/file_manager|/adminer"
    r"|/xmlrpc\.php|/setup\.php|/install\.php|/CHANGELOG"
    r"|/LICENSE|/README|/web\.config|/crossdomain\.xml"
    r"|/sitemap\.xml.*\.\.|\.bak$|\.old$|\.orig$|\.swp$)",
    re.IGNORECASE,
)

_SENSITIVE_HEADER_PATTERNS = re.compile(
    r"(X-Forwarded-For.*,.*,|X-Real-IP.*,|True-Client-IP.*,)",
    re.IGNORECASE,
)

# Known Tor exit node ranges (simplified — first octets of known Tor IP blocks)
_TOR_INDICATORS = {
    "176.10.99.", "185.220.", "199.87.154.", "162.247.72.", "23.129.64.",
    "171.25.193.", "5.2.72.", "192.42.116.", "tor-exit", "tor.dan.",
}

# Known datacenter / VPN provider CIDR blocks (representative samples)
_DATACENTER_PREFIXES = [
    "104.16.", "104.17.", "104.18.", "104.19.",   # Cloudflare
    "172.64.", "172.65.", "172.66.", "172.67.",   # Cloudflare
    "13.32.", "13.33.", "13.34.", "13.35.",       # Amazon CloudFront
    "34.", "35.", "130.211.", "104.154.",          # Google Cloud (broad)
    "52.", "54.",                                  # AWS (broad)
    "40.", "13.", "20.", "23.",                    # Azure (broad)
    "45.33.", "45.56.", "45.79.",                  # Linode
    "192.155.", "198.199.", "167.99.",             # DigitalOcean
    "95.216.", "95.217.", "65.108.",               # Hetzner
]

# Bogon / private network ranges
_PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

# High-risk countries by ISO code (simplified, for demonstration)
_HIGH_RISK_COUNTRY_CODES = {"KP", "IR", "SY", "CU", "SD", "RU", "BY"}


# ---------------------------------------------------------------------------
# GeoIPLookup (pattern-based, no external DB required)
# ---------------------------------------------------------------------------

class GeoIPLookup:
    """
    Simplified pattern-based GeoIP lookup.
    Does NOT use a real GeoIP database — provides best-effort estimates
    based on known IP allocation patterns and reverse-DNS patterns.
    Replace with MaxMind GeoLite2 or similar for production accuracy.
    """

    # Representative country IP range prefixes (first two octets)
    _COUNTRY_MAP = {
        "1.32": "SG",  "1.33": "SG",  "1.34": "AU",  "1.35": "AU",
        "1.2":  "CN",  "1.4":  "CN",  "5.45": "DE",  "5.79": "NL",
        "5.188": "RU", "8.8":  "US",  "8.34": "US",  "13.":  "US",
        "23.":  "US",  "31.":  "EU",  "34.":  "US",  "35.":  "US",
        "40.":  "US",  "45.":  "US",  "46.":  "EU",  "52.":  "US",
        "54.":  "US",  "62.":  "EU",  "64.":  "US",  "66.":  "US",
        "67.":  "US",  "68.":  "US",  "69.":  "US",  "70.":  "US",
        "71.":  "US",  "72.":  "US",  "74.":  "US",  "75.":  "US",
        "76.":  "US",  "95.":  "EU",  "104.": "US",  "108.": "US",
        "130.": "US",  "131.": "US",  "138.": "AU",  "139.": "SG",
        "149.": "US",  "162.": "US",  "163.": "US",  "167.": "US",
        "172.": "US",  "173.": "US",  "174.": "US",  "176.": "DE",
        "178.": "EU",  "182.": "CN",  "183.": "CN",  "185.": "EU",
        "188.": "EU",  "190.": "SV",  "192.": "US",  "193.": "EU",
        "194.": "EU",  "195.": "EU",  "198.": "US",  "199.": "US",
        "200.": "MX",  "201.": "BR",  "202.": "CN",  "203.": "AU",
        "204.": "US",  "205.": "US",  "206.": "US",  "207.": "US",
        "208.": "US",  "209.": "US",  "210.": "AU",  "211.": "JP",
        "212.": "EU",  "213.": "EU",  "216.": "US",  "217.": "EU",
    }

    @classmethod
    def lookup(cls, ip: str) -> dict:
        """
        Attempt to determine country/region from IP address.
        Returns a dict with best-effort geo information.
        """
        if not ip or not isinstance(ip, str):
            return {"ip": ip, "country": "XX", "region": "Unknown", "confidence": 0}

        ip = ip.strip()

        # Check private/local ranges first
        try:
            ip_obj = ipaddress.ip_address(ip)
            for net in _PRIVATE_RANGES:
                if ip_obj in net:
                    return {
                        "ip": ip, "country": "LOCAL",
                        "region": "Private Network", "confidence": 95,
                        "is_private": True,
                    }
        except ValueError:
            return {"ip": ip, "country": "XX", "region": "Unknown", "confidence": 0}

        # Match against known prefixes (longest match first)
        parts = ip.split(".")
        best_match = None
        best_len = 0

        for prefix, country in cls._COUNTRY_MAP.items():
            if ip.startswith(prefix) and len(prefix) > best_len:
                best_match = country
                best_len = len(prefix)

        country = best_match or "XX"
        is_high_risk = country in _HIGH_RISK_COUNTRY_CODES

        return {
            "ip":          ip,
            "country":     country,
            "region":      "Unknown",
            "confidence":  60 if best_match else 10,
            "is_private":  False,
            "is_high_risk": is_high_risk,
        }

    @classmethod
    def is_tor_exit(cls, ip: str) -> bool:
        """Heuristic check for Tor exit node IPs."""
        if not isinstance(ip, str):
            return False
        return any(ip.startswith(prefix) for prefix in _TOR_INDICATORS if "." in prefix)

    @classmethod
    def is_vpn(cls, ip: str) -> bool:
        """Heuristic check for known VPN provider IP ranges."""
        if not isinstance(ip, str):
            return False
        # Simple heuristic: datacenter IPs are often used by VPNs
        return cls.is_datacenter(ip)

    @classmethod
    def is_datacenter(cls, ip: str) -> bool:
        """Heuristic check for datacenter / hosting provider IP ranges."""
        if not isinstance(ip, str):
            return False
        return any(ip.startswith(prefix) for prefix in _DATACENTER_PREFIXES)


# ---------------------------------------------------------------------------
# ThreatDetector
# ---------------------------------------------------------------------------

class ThreatDetector:
    """
    Real-time threat detection engine.

    Maintains in-memory state (request logs, blocked IPs) and analyzes
    incoming requests for malicious patterns.
    """

    _instance: Optional["ThreatDetector"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ThreatDetector":
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._initialized = False
                cls._instance = inst
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            # ip → list of (timestamp, path, method, ua)
            self._request_log: dict[str, list] = {}
            # ip → {"reason": str, "blocked_until": int}
            self._blocked_ips: dict[str, dict] = {}
            # ip → {"score": int, "reasons": list}
            self._threat_scores: dict[str, dict] = {}
            self._geo = GeoIPLookup()
            self._initialized = True

    # ------------------------------------------------------------------
    # Core analysis
    # ------------------------------------------------------------------

    def analyze_request(
        self,
        ip: str,
        method: str,
        path: str,
        headers: dict,
        body: str = "",
    ) -> dict:
        """
        Analyze an incoming HTTP request and return a threat assessment.

        Returns::

            {
                "threat_score": int,       # 0-100
                "blocked":      bool,
                "reasons":      [str],
                "recommended_action": str  # "allow" | "challenge" | "block"
            }
        """
        reasons = []
        score = 0

        # Check if already blocked
        if self.is_blocked(ip):
            return {
                "threat_score": 100,
                "blocked": True,
                "reasons": ["IP is on blocklist"],
                "recommended_action": "block",
                "geo": self._geo.lookup(ip),
            }

        ua = headers.get("User-Agent", headers.get("user-agent", ""))

        # 1. Bot/scanner user agent
        if self.detect_bot(ua, {}):
            reasons.append("Suspicious user-agent detected")
            score += 40

        # 2. Path scanning patterns
        if _SCANNER_PATH_PATTERNS.search(path):
            reasons.append("Path matches known scanner/exploit pattern")
            score += 50

        # 3. Missing typical browser headers
        if not ua:
            reasons.append("Empty User-Agent header")
            score += 20
        elif len(ua) < 10:
            reasons.append("Unusually short User-Agent")
            score += 15

        # 4. High-frequency requests from same IP
        self._record_request(ip, path, method, ua)
        recent = self._get_recent_requests(ip, window=60)
        if len(recent) > 60:
            reasons.append(f"High request rate: {len(recent)} req/min")
            score += min(40, len(recent) - 60)

        # 5. Scanning detection (many different paths in short window)
        if self.detect_scanning(ip, recent):
            reasons.append("Path scanning behavior detected")
            score += 35

        # 6. GeoIP risk
        geo = self._geo.lookup(ip)
        if geo.get("is_high_risk"):
            reasons.append(f"High-risk country: {geo.get('country')}")
            score += 15

        if self._geo.is_tor_exit(ip):
            reasons.append("Tor exit node detected")
            score += 25

        if self._geo.is_datacenter(ip):
            reasons.append("Datacenter / hosting IP")
            score += 10

        # 7. Suspicious headers
        for k, v in headers.items():
            if _SENSITIVE_HEADER_PATTERNS.search(f"{k}: {v}"):
                reasons.append("Suspicious proxy chain in headers")
                score += 10
                break

        score = min(100, score)

        # Update threat score cache
        self._threat_scores[ip] = {
            "score":     score,
            "reasons":   reasons,
            "updated_at": int(time.time()),
        }

        action = (
            "block"     if score >= 70 else
            "challenge" if score >= 40 else
            "allow"
        )

        return {
            "threat_score":       score,
            "blocked":            False,
            "reasons":            reasons,
            "recommended_action": action,
            "geo":                geo,
            "request_rate_1m":    len(recent),
        }

    # ------------------------------------------------------------------
    # Detection methods
    # ------------------------------------------------------------------

    def detect_bot(self, user_agent: str, request_pattern: dict) -> bool:
        """Detect automated bot traffic based on user-agent and patterns."""
        if not isinstance(user_agent, str):
            return True  # No UA = likely a bot

        if not user_agent.strip():
            return True

        if _BOT_UA_PATTERNS.search(user_agent):
            return True

        # Extremely short UAs are suspicious
        if len(user_agent) < 10:
            return True

        return False

    def detect_scanning(self, ip: str, recent_requests: list) -> bool:
        """
        Detect path/port scanning behavior: many unique paths from one IP
        in a short time window.
        """
        if not recent_requests:
            return False

        unique_paths = {req.get("path", "") for req in recent_requests}

        # More than 30 unique paths in the window = scanning
        if len(unique_paths) > 30:
            return True

        # Check for sequential numeric or alphabetical patterns
        numeric_paths = [p for p in unique_paths if re.search(r"/\d+$", p)]
        if len(numeric_paths) > 15:
            return True

        # Check for common wordlist patterns (dictionary attack on paths)
        wordlist_hits = sum(
            1 for p in unique_paths
            if _SCANNER_PATH_PATTERNS.search(p)
        )
        if wordlist_hits > 3:
            return True

        return False

    def detect_credential_stuffing(
        self, ip: str, auth_attempts: list
    ) -> bool:
        """
        Detect credential stuffing: many auth attempts with different
        pubkeys from the same IP in a short window.
        """
        if not auth_attempts:
            return False

        unique_pubkeys = {a.get("pubkey", "") for a in auth_attempts}
        timestamps = sorted(a.get("timestamp", 0) for a in auth_attempts)

        if not timestamps:
            return False

        window = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0

        # More than 5 different pubkeys in 10 minutes = credential stuffing
        if len(unique_pubkeys) >= 5 and window <= 600:
            return True

        # More than 20 attempts in 1 hour
        if len(auth_attempts) >= 20 and window <= 3600:
            return True

        return False

    def detect_api_abuse(self, ip: str, request_log: list) -> dict:
        """
        Detect API abuse patterns: excessive calls to expensive endpoints,
        bulk data extraction, etc.
        """
        if not request_log:
            return {"abuse": False, "type": None, "score": 0}

        expensive_endpoints = {
            "/api/savings/projection", "/api/pension/projection",
            "/api/remittance/calculate", "/api/market/history",
            "/api/export", "/api/admin",
        }

        expensive_count = sum(
            1 for r in request_log
            if any(r.get("path", "").startswith(ep) for ep in expensive_endpoints)
        )

        total = len(request_log)
        window = max(1, (
            max(r.get("timestamp", 0) for r in request_log) -
            min(r.get("timestamp", 0) for r in request_log)
        ))

        rps = total / max(window, 1)

        score = 0
        abuse_type = None

        if expensive_count > 50:
            score += 60
            abuse_type = "expensive_endpoint_hammering"

        if rps > 10:
            score += 40
            abuse_type = abuse_type or "high_rps"

        if total > 1000 and window < 3600:
            score += 30
            abuse_type = abuse_type or "bulk_scraping"

        return {
            "abuse":   score >= 50,
            "type":    abuse_type,
            "score":   min(100, score),
            "total_requests": total,
            "window_seconds": window,
            "rps":    round(rps, 2),
        }

    def detect_data_exfiltration(
        self, pubkey: str, export_requests: list
    ) -> bool:
        """
        Detect unusual data export / access patterns that may indicate
        data exfiltration attempts.
        """
        if not export_requests:
            return False

        # More than 5 full exports in 24 hours
        window_24h = int(time.time()) - 86400
        recent = [
            r for r in export_requests
            if r.get("timestamp", 0) >= window_24h
        ]

        if len(recent) > 5:
            return True

        # Check for bulk access to /export or large data downloads
        bulk_exports = sum(
            1 for r in recent
            if "/export" in r.get("path", "") or r.get("bytes_sent", 0) > 1_000_000
        )

        return bulk_exports > 3

    # ------------------------------------------------------------------
    # Threat level
    # ------------------------------------------------------------------

    def get_threat_level(self) -> dict:
        """
        Return the current overall system threat level based on
        recent activity in the in-memory request log.
        """
        now = int(time.time())
        window = 300  # last 5 minutes

        total_requests = 0
        suspicious_ips = 0
        blocked_count = len(self._blocked_ips)

        for ip, log in self._request_log.items():
            recent = [e for e in log if e.get("timestamp", 0) >= now - window]
            if recent:
                total_requests += len(recent)
                if ip in self._threat_scores and self._threat_scores[ip]["score"] >= 70:
                    suspicious_ips += 1

        # Expire blocked IPs
        self._blocked_ips = {
            ip: data for ip, data in self._blocked_ips.items()
            if data.get("blocked_until", 0) > now or data.get("blocked_until") == 0
        }

        score = min(100, (suspicious_ips * 10) + (blocked_count * 5))

        level = (
            "CRITICAL" if score >= 80 else
            "HIGH"     if score >= 60 else
            "ELEVATED" if score >= 40 else
            "MODERATE" if score >= 20 else
            "LOW"
        )

        return {
            "level":           level,
            "score":           score,
            "active_ips_5m":   total_requests,
            "suspicious_ips":  suspicious_ips,
            "blocked_ips":     blocked_count,
            "timestamp":       now,
        }

    # ------------------------------------------------------------------
    # IP blocklist management
    # ------------------------------------------------------------------

    def get_blocked_ips(self) -> list:
        """Return a list of currently blocked IPs with details."""
        now = int(time.time())
        result = []
        for ip, data in list(self._blocked_ips.items()):
            blocked_until = data.get("blocked_until", 0)
            if blocked_until != 0 and blocked_until <= now:
                del self._blocked_ips[ip]
                continue
            result.append({
                "ip":            ip,
                "reason":        data.get("reason", ""),
                "blocked_at":    data.get("blocked_at", 0),
                "blocked_until": blocked_until,
                "permanent":     blocked_until == 0,
            })
        return result

    def block_ip(self, ip: str, reason: str = "", duration: int = 3600) -> None:
        """
        Block an IP address.
        ``duration`` is in seconds. 0 means permanent.
        """
        if not ip:
            return

        now = int(time.time())
        self._blocked_ips[ip] = {
            "reason":        reason or "Blocked by threat detection",
            "blocked_at":    now,
            "blocked_until": (now + duration) if duration > 0 else 0,
        }

    def unblock_ip(self, ip: str) -> bool:
        """Remove an IP from the blocklist. Returns True if it was blocked."""
        if ip in self._blocked_ips:
            del self._blocked_ips[ip]
            return True
        return False

    def is_blocked(self, ip: str) -> bool:
        """Check if an IP is currently blocked."""
        if ip not in self._blocked_ips:
            return False

        data = self._blocked_ips[ip]
        blocked_until = data.get("blocked_until", 0)

        if blocked_until == 0:  # Permanent
            return True

        if blocked_until > int(time.time()):
            return True

        # Expired — clean up
        del self._blocked_ips[ip]
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_request(
        self, ip: str, path: str, method: str, ua: str
    ) -> None:
        """Record a request in the in-memory log (capped at 500 per IP)."""
        if ip not in self._request_log:
            self._request_log[ip] = []

        self._request_log[ip].append({
            "timestamp": int(time.time()),
            "path":      path,
            "method":    method,
            "ua":        ua,
        })

        # Cap memory usage per IP
        if len(self._request_log[ip]) > 500:
            self._request_log[ip] = self._request_log[ip][-200:]

    def _get_recent_requests(self, ip: str, window: int = 60) -> list:
        """Return requests from an IP within the last ``window`` seconds."""
        if ip not in self._request_log:
            return []

        cutoff = int(time.time()) - window
        return [r for r in self._request_log[ip] if r.get("timestamp", 0) >= cutoff]

    def purge_old_records(self, older_than: int = 3600) -> int:
        """
        Remove old request log entries to free memory.
        Returns number of IP entries cleared.
        """
        cutoff = int(time.time()) - older_than
        cleared = 0

        for ip in list(self._request_log.keys()):
            self._request_log[ip] = [
                r for r in self._request_log[ip]
                if r.get("timestamp", 0) >= cutoff
            ]
            if not self._request_log[ip]:
                del self._request_log[ip]
                cleared += 1

        return cleared
