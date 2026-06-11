#!/usr/bin/env python3
"""
LawPhil Case Downloader - Multi-Browser & Absolute Path Version
A tool to download Philippine Supreme Court cases from lawphil.net as PDF files.

Usage:
    python download.py "G.R. No. 238659"
"""

import sys
import re
import os
import argparse
from datetime import datetime
import time
import base64

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
except ImportError:
    print("Error: Selenium not installed.")
    print("Please run: pip install selenium")
    sys.exit(1)


class LawPhilDownloader:
    """Downloads cases from lawphil.net and saves them as PDF."""
    
    SEARCH_URL = "https://www.google.com/search?q=site:lawphil.net+"
    
    def __init__(self, headless=True):
        """Initialize the downloader with browser options."""
        self.headless = headless
        self.driver = None
        
    def setup_driver(self):
        """Attempts to launch Google Chrome first, falls back to Microsoft Edge."""
        common_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-blink-features=AutomationControlled'
        ]
        if self.headless:
            common_args.append('--headless=new')

        # --- 1. TRY GOOGLE CHROME FIRST ---
        try:
            chrome_options = ChromeOptions()
            for arg in common_args:
                chrome_options.add_argument(arg)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_experimental_option("prefs", {
                "profile.default_content_setting_values.notifications": 2,
                "profile.cookie_controls_mode": 0
            })
            
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✓ Google Chrome started successfully")
            return
        except Exception:
            # If Chrome fails or isn't installed, silently pass to try Edge
            pass

        # --- 2. FALLBACK TO MICROSOFT EDGE ---
        try:
            edge_options = EdgeOptions()
            for arg in common_args:
                edge_options.add_argument(arg)
            edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            edge_options.add_experimental_option('useAutomationExtension', False)
            edge_options.add_experimental_option("prefs", {
                "profile.default_content_setting_values.notifications": 2,
                "profile.cookie_controls_mode": 0
            })
            
            self.driver = webdriver.Edge(options=edge_options)
            print("✓ Microsoft Edge started successfully")
            return
        except Exception as e:
            print(f"Error: Could not start either Google Chrome or Edge browser: {e}")
            print("\nMake sure a compatible Chromium browser is installed and updated.")
            raise
    
    def format_case_number(self, case_input):
        """Format case number - if just digits, add G.R. No. prefix."""
        case_input = case_input.strip()
        
        if case_input.isdigit():
            formatted = f"G.R. No. {case_input}"
            print(f"Formatted as: {formatted}")
            return formatted, case_input
        else:
            match = re.search(r'(\d+)', case_input)
            number_only = match.group(1) if match else case_input
            return case_input, number_only
    
    def search_and_get_first_link(self, search_term, case_number_only=None):
        """Search on Google with site:lawphil.net and return first result."""
        search_query = search_term.replace(" ", "+")
        search_url = f"{self.SEARCH_URL}{search_query}"
        
        print(f"Searching for: {search_term}")
        print(f"Search URL: {search_url}")
        
        self.case_number_only = case_number_only
        self.driver.get(search_url)
        time.sleep(3)
        
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href]")
            for link in links:
                href = link.get_attribute('href')
                if href and 'lawphil.net' in href and 'judjuris' in href and '.html' in href:
                    if not href.startswith('https://www.google.com'):
                        print(f"✓ Found case: {href}")
                        return href
            
            print("✗ No case found in search results")
            return None
            
        except Exception as e:
            print(f"Error searching: {e}")
            return None
    
    def close_popups_and_accept_cookies(self):
        """Try to close cookie popups and any overlays."""
        try:
            time.sleep(1)
            cookie_selectors = [
                "button[id*='accept']", "button[class*='accept']", "a[id*='accept']", "a[class*='accept']",
                "button[id*='cookie']", "button[class*='cookie']", "button[id*='consent']", "button[class*='consent']",
                "button:contains('Accept')", "button:contains('I agree')", "button:contains('OK')",
                "[class*='cookie-accept']", "[id*='cookie-accept']",
            ]
            
            for selector in cookie_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.click()
                            print("✓ Closed cookie popup")
                            time.sleep(0.5)
                            break
                except:
                    continue
            
            overlay_selectors = [
                "[class*='modal']", "[class*='overlay']", "[class*='popup']",
                "[id*='modal']", "[id*='overlay']", "[id*='popup']",
            ]
            
            for selector in overlay_selectors:
                try:
                    overlays = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for overlay in overlays:
                        if overlay.is_displayed():
                            close_buttons = overlay.find_elements(By.CSS_SELECTOR, 
                                "button[class*='close'], a[class*='close'], [aria-label*='close'], [title*='close']")
                            for btn in close_buttons:
                                try:
                                    btn.click()
                                    print("✓ Closed popup overlay")
                                    time.sleep(0.5)
                                    break
                                except:
                                    continue
                except:
                    continue
                    
        except Exception:
            pass
    
    def save_page_as_pdf(self, url, output_filename=None):
        """Open a URL and save the page as PDF directly in the application folder."""
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
            
            # --- FIX: Dynamically target the exact folder where the script or .exe lives ---
            if getattr(sys, 'frozen', False):
                # Running as a compiled PyInstaller executable (.exe)
                app_dir = os.path.dirname(sys.executable)
            else:
                # Running as a standard raw python script (.py)
                app_dir = os.path.dirname(os.path.abspath(__file__))
                
            absolute_output_path = os.path.join(app_dir, output_filename)
            print(f"Saving explicitly to: {absolute_output_path}")
            
            pdf_settings = {
                "landscape": False,
                "displayHeaderFooter": False,
                "printBackground": True,
                "preferCSSPageSize": False,
                "paperWidth": 8.27,  # A4 width in inches
                "paperHeight": 11.69,  # A4 height in inches
                "marginTop": 0.4,
                "marginBottom": 0.4,
                "marginLeft": 0.4,
                "marginRight": 0.4,
            }
            
            # Chromium DevTools Protocol command (supported identically by Chrome & Edge)
            result = self.driver.execute_cdp_cmd("Page.printToPDF", pdf_settings)
            
            # Decode and save PDF to the absolute path
            with open(absolute_output_path, 'wb') as f:
                f.write(base64.b64decode(result['data']))
            
            print(f"✓ Successfully saved: {absolute_output_path}")
            return True
            
        except Exception as e:
            print(f"✗ Error saving PDF: {e}")
            return False
    
    def download_case(self, search_input, output_filename=None):
        """Main method: search for case and download first result."""
        try:
            self.setup_driver()
            search_term, case_number_only = self.format_case_number(search_input)
            case_url = self.search_and_get_first_link(search_term, case_number_only)
            
            if not case_url:
                print("Could not find any case. Try a different search term.")
                return False
            
            return self.save_page_as_pdf(case_url, output_filename)
                
        except Exception as e:
            print(f"Error: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
    
    def download_from_url(self, url, output_filename=None):
        """Download a case directly from a URL."""
        try:
            self.setup_driver()
            return self.save_page_as_pdf(url, output_filename)
        except Exception as e:
            print(f"Error: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Download Philippine Supreme Court cases from lawphil.net as PDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 238659
  %(prog)s 227868 -o my_case.pdf
  %(prog)s "G.R. No. 238659"
  %(prog)s --url "https://lawphil.net/judjuris/juri2019/jun2019/gr_238659_2019.html"
  %(prog)s 238659 --show-browser
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('search_term', nargs='?', 
                      help='Case number (just digits like "238659" or full format "G.R. No. 238659")')
    group.add_argument('--url', help='Direct URL to a case on lawphil.net')
    
    parser.add_argument('-o', '--output', help='Output PDF filename')
    parser.add_argument('--show-browser', action='store_true', 
                       help='Show browser window (default: hidden)')
    
    args = parser.parse_args()
    
    downloader = LawPhilDownloader(headless=not args.show_browser)
    
    if args.url:
        print("Mode: Direct URL download")
        success = downloader.download_from_url(args.url, args.output)
    else:
        print("Mode: Search and download first result")
        success = downloader.download_case(args.search_term, args.output)
    
    if success:
        print("\n✓ Done!")
    else:
        print("\n✗ Failed!")
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()