#!/usr/bin/env python3
"""
LawPhil Case Downloader - Multi-Case Version
A tool to download Philippine Supreme Court cases from lawphil.net as PDF files.

Usage examples:
    python d1.py 238659
    python d1.py 82585,227635
    python d1.py 82585 227635
    python d1.py "G.R. No. 238659"
    python d1.py --url "https://lawphil.net/judjuris/juri2019/jun2019/gr_238659_2019.html"
"""

import sys
import re
import os
import argparse
from datetime import datetime
import time

try:
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    print("Error: Selenium not installed.")
    print("Please run: pip install selenium")
    sys.exit(1)


class LawPhilDownloader:
    """Downloads cases from lawphil.net and saves them as PDF."""
    
    SEARCH_URL = "https://www.google.com/search?q=site:lawphil.net+"
    
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        
    def setup_driver(self):
        """Set up Selenium WebDriver with Microsoft Edge."""
        if self.driver:
            return  # Reuse if already running
        
        edge_options = Options()
        if self.headless:
            edge_options.add_argument('--headless=new')
        edge_options.add_argument('--no-sandbox')
        edge_options.add_argument('--disable-dev-shm-usage')
        edge_options.add_argument('--disable-gpu')
        edge_options.add_argument('--disable-blink-features=AutomationControlled')
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_experimental_option('useAutomationExtension', False)
        edge_options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
        )
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.cookie_controls_mode": 0
        }
        edge_options.add_experimental_option("prefs", prefs)
        
        try:
            self.driver = webdriver.Edge(options=edge_options)
            print("✓ Browser started successfully")
        except Exception as e:
            print(f"Error: Could not start Edge browser: {e}")
            print("Make sure Microsoft Edge is installed and updated.")
            raise

    def close_driver(self):
        """Close the browser if open."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def format_case_number(self, case_input):
        case_input = case_input.strip()
        if case_input.isdigit():
            formatted = f"G.R. No. {case_input}"
            return formatted, case_input
        else:
            match = re.search(r'(\d+)', case_input)
            number_only = match.group(1) if match else case_input
            return case_input, number_only
    
    def search_and_get_first_link(self, search_term, case_number_only=None):
        search_query = search_term.replace(" ", "+")
        search_url = f"{self.SEARCH_URL}{search_query}"
        print(f"Searching for: {search_term}")
        print(f"Search URL: {search_url}")
        self.case_number_only = case_number_only
        self.driver.get(search_url)
        time.sleep(4)
        try:
            selectors = [
                "div#search a[href*='lawphil.net']",
                "div.g a[href*='lawphil.net']",
                "a[href*='lawphil.net'][href*='judjuris']",
                "a[jsname]",
                "h3 a",
            ]
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute('href')
                    if href and 'lawphil.net' in href and 'judjuris' in href and '.html' in href:
                        if not href.startswith('https://www.google.com'):
                            print(f"✓ Found case: {href}")
                            return href
            print("Trying to parse page source...")
            page_source = self.driver.page_source
            pattern = r'https://lawphil\.net/judjuris/[^"\'<>\s]+'
            matches = re.findall(pattern, page_source)
            if matches:
                for match in matches:
                    if '.html' in match:
                        print(f"✓ Found case: {match}")
                        return match
            print("✗ No case found in search results")
            return None
        except Exception as e:
            print(f"Error searching: {e}")
            return None
    
    def close_popups_and_accept_cookies(self):
        try:
            time.sleep(1)
            cookie_selectors = [
                "button[id*='accept']",
                "button[class*='accept']",
                "a[id*='accept']",
                "a[class*='accept']",
                "button[id*='cookie']",
                "button[class*='cookie']",
                "button[id*='consent']",
                "button[class*='consent']",
                "[class*='cookie-accept']",
                "[id*='cookie-accept']",
            ]
            for selector in cookie_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        element.click()
                        print("✓ Closed cookie popup")
                        time.sleep(0.5)
                        break
        except Exception:
            pass
    
    def save_page_as_pdf(self, url, output_filename=None):
        if not url:
            print("No URL provided")
            return False
        print(f"Opening: {url}")
        self.driver.get(url)
        time.sleep(2)
        self.close_popups_and_accept_cookies()
        try:
            if not output_filename:
                if hasattr(self, 'case_number_only') and self.case_number_only:
                    output_filename = f"G.R. No. {self.case_number_only}.pdf"
                else:
                    page_title = self.driver.title
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_filename = f"{page_title[:50].replace(' ', '_')}_{timestamp}.pdf"
                    output_filename = re.sub(r'[<>:"/\\|?*]', '', output_filename)
            if not output_filename.endswith('.pdf'):
                output_filename += '.pdf'
            print(f"Saving as: {output_filename}")
            import base64
            pdf_settings = {
                "landscape": False,
                "displayHeaderFooter": False,
                "printBackground": True,
                "preferCSSPageSize": False,
                "paperWidth": 8.27,
                "paperHeight": 11.69,
                "marginTop": 0.4,
                "marginBottom": 0.4,
                "marginLeft": 0.4,
                "marginRight": 0.4,
            }
            result = self.driver.execute_cdp_cmd("Page.printToPDF", pdf_settings)
            with open(output_filename, 'wb') as f:
                f.write(base64.b64decode(result['data']))
            print(f"✓ Successfully saved: {output_filename}")
            return True
        except Exception as e:
            print(f"✗ Error saving PDF: {e}")
            return False
    
    def download_case(self, search_input, output_filename=None):
        """Search and download a case (reuses existing browser)."""
        self.setup_driver()
        search_term, case_number_only = self.format_case_number(search_input)
        case_url = self.search_and_get_first_link(search_term, case_number_only)
        if not case_url:
            print(f"✗ Could not find case for {search_input}")
            return False
        return self.save_page_as_pdf(case_url, output_filename)
    
    def download_from_url(self, url, output_filename=None):
        self.setup_driver()
        return self.save_page_as_pdf(url, output_filename)


def main():
    parser = argparse.ArgumentParser(
        description='Download Philippine Supreme Court cases from lawphil.net as PDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 238659
  %(prog)s 227868 -o my_case.pdf
  %(prog)s 82585,227635
  %(prog)s 82585 227635
  %(prog)s --url "https://lawphil.net/judjuris/juri2019/jun2019/gr_238659_2019.html"
  %(prog)s 238659 --show-browser
        """
    )

    parser.add_argument('search_terms', nargs='*', help='Case numbers (comma-separated or space-separated)')
    parser.add_argument('--url', help='Direct URL to a case on lawphil.net')
    parser.add_argument('-o', '--output', help='Output PDF filename (only for single download)')
    parser.add_argument('--show-browser', action='store_true', help='Show browser window (default: hidden)')
    args = parser.parse_args()

    downloader = LawPhilDownloader(headless=not args.show_browser)

    try:
        if args.url:
            print("Mode: Direct URL download")
            success = downloader.download_from_url(args.url, args.output)
            sys.exit(0 if success else 1)

        if not args.search_terms:
            parser.print_help()
            sys.exit(1)

        # Split comma-separated lists into individual numbers
        case_numbers = []
        for term in args.search_terms:
            case_numbers.extend([c.strip() for c in term.split(',') if c.strip()])

        print(f"Detected {len(case_numbers)} case(s): {', '.join(case_numbers)}")

        all_success = True
        downloader.setup_driver()

        for case_number in case_numbers:
            print(f"\n=== Downloading case {case_number} ===")
            success = downloader.download_case(case_number)
            if not success:
                all_success = False
            print(f"--- Finished case {case_number} ---\n")

        if all_success:
            print("\n✓ All downloads completed successfully!")
        else:
            print("\n✗ Some downloads failed.")

    finally:
        downloader.close_driver()


if __name__ == '__main__':
    main()
