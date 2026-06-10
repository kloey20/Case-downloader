#!/usr/bin/env python3
"""
LawPhil Case Downloader - Simplified Version
A tool to download Philippine Supreme Court cases from lawphil.net as PDF files.

Usage:
    python lawphil_downloader.py "G.R. No. 238659"
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
        """Set up Selenium WebDriver with Microsoft Edge."""
        edge_options = Options()
        
        if self.headless:
            edge_options.add_argument('--headless=new')
        
        edge_options.add_argument('--no-sandbox')
        edge_options.add_argument('--disable-dev-shm-usage')
        edge_options.add_argument('--disable-gpu')
        edge_options.add_argument('--disable-blink-features=AutomationControlled')
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_experimental_option('useAutomationExtension', False)
        
        # Add user agent to look more like a real browser
        edge_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0')
        
        # Disable cookie popups and notifications
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
            print("\nMake sure Microsoft Edge is installed and updated.")
            raise
    
    def format_case_number(self, case_input):
        """Format case number - if just digits, add G.R. No. prefix."""
        case_input = case_input.strip()
        
        # If it's just numbers, format as G.R. No.
        if case_input.isdigit():
            formatted = f"G.R. No. {case_input}"
            print(f"Formatted as: {formatted}")
            return formatted, case_input
        else:
            # Already formatted or different format
            # Try to extract just the number for filename
            match = re.search(r'(\d+)', case_input)
            number_only = match.group(1) if match else case_input
            return case_input, number_only
    
    def search_and_get_first_link(self, search_term, case_number_only=None):
        """Search on Google with site:lawphil.net and return first result."""
        # Construct search URL
        search_query = search_term.replace(" ", "+")
        search_url = f"{self.SEARCH_URL}{search_query}"
        
        print(f"Searching for: {search_term}")
        print(f"Search URL: {search_url}")
        
        # Store case number for later use in filename
        self.case_number_only = case_number_only
        
        self.driver.get(search_url)
        time.sleep(4)  # Wait longer for page to load
        
        try:
            # Try multiple methods to find links
            
            # Method 1: Try standard search result selectors
            selectors = [
                "div#search a[href*='lawphil.net']",
                "div.g a[href*='lawphil.net']",
                "a[href*='lawphil.net'][href*='judjuris']",
                "a[jsname]",
                "h3 a",
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        href = element.get_attribute('href')
                        if href and 'lawphil.net' in href and 'judjuris' in href and '.html' in href:
                            if not href.startswith('https://www.google.com'):
                                print(f"✓ Found case: {href}")
                                return href
                except:
                    continue
            
            # Method 2: Get ALL links and filter
            print("Trying alternative search method...")
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    if href and 'lawphil.net' in href and 'judjuris' in href and '.html' in href:
                        if not href.startswith('https://www.google.com') and '/url?' not in href:
                            print(f"✓ Found case: {href}")
                            return href
                except:
                    continue
            
            # Method 3: Try to get the page source and parse it
            print("Trying to parse page source...")
            page_source = self.driver.page_source
            
            # Look for lawphil URLs in the page source
            import re
            pattern = r'https://lawphil\.net/judjuris/[^"\'<>\s]+'
            matches = re.findall(pattern, page_source)
            
            if matches:
                for match in matches:
                    if '.html' in match:
                        print(f"✓ Found case: {match}")
                        return match
            
            print("✗ No case found in search results")
            print("Tip: Try running with --show-browser to see what's happening")
            return None
            
        except Exception as e:
            print(f"Error searching: {e}")
            return None
    
    def close_popups_and_accept_cookies(self):
        """Try to close cookie popups and any overlays."""
        try:
            # Wait a moment for popups to appear
            time.sleep(1)
            
            # Common cookie accept button selectors
            cookie_selectors = [
                "button[id*='accept']",
                "button[class*='accept']",
                "a[id*='accept']",
                "a[class*='accept']",
                "button[id*='cookie']",
                "button[class*='cookie']",
                "button[id*='consent']",
                "button[class*='consent']",
                "button:contains('Accept')",
                "button:contains('I agree')",
                "button:contains('OK')",
                "[class*='cookie-accept']",
                "[id*='cookie-accept']",
            ]
            
            # Try to find and click cookie accept buttons
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
            
            # Try to close any modal dialogs or overlays
            overlay_selectors = [
                "[class*='modal']",
                "[class*='overlay']",
                "[class*='popup']",
                "[id*='modal']",
                "[id*='overlay']",
                "[id*='popup']",
            ]
            
            for selector in overlay_selectors:
                try:
                    # Look for close buttons within overlays
                    overlays = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for overlay in overlays:
                        if overlay.is_displayed():
                            # Try to find close button
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
                    
        except Exception as e:
            # Don't fail if we can't close popups, just continue
            pass
    
    def save_page_as_pdf(self, url, output_filename=None):
        """Open a URL and save the page as PDF."""
        if not url:
            print("No URL provided")
            return False
        
        print(f"Opening: {url}")
        self.driver.get(url)
        time.sleep(2)  # Wait for page to load
        
        # Try to close cookie popups and overlays
        self.close_popups_and_accept_cookies()
        
        try:
            # Generate filename if not provided
            if not output_filename:
                # Use the case number only if available
                if hasattr(self, 'case_number_only') and self.case_number_only:
                    output_filename = f"G.R. No. {self.case_number_only}.pdf"
                else:
                    # Fallback to page title
                    page_title = self.driver.title
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_filename = f"{page_title[:50].replace(' ', '_')}_{timestamp}.pdf"
                    # Clean filename - remove invalid characters
                    output_filename = re.sub(r'[<>:"/\\|?*]', '', output_filename)
            
            if not output_filename.endswith('.pdf'):
                output_filename += '.pdf'
            
            print(f"Saving as: {output_filename}")
            
            # Use Chrome DevTools Protocol to print to PDF
            import base64
            
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
            
            result = self.driver.execute_cdp_cmd("Page.printToPDF", pdf_settings)
            
            # Decode and save PDF
            with open(output_filename, 'wb') as f:
                f.write(base64.b64decode(result['data']))
            
            print(f"✓ Successfully saved: {output_filename}")
            return True
            
        except Exception as e:
            print(f"✗ Error saving PDF: {e}")
            return False
    
    def download_case(self, search_input, output_filename=None):
        """Main method: search for case and download first result."""
        try:
            self.setup_driver()
            
            # Format the case number if needed
            search_term, case_number_only = self.format_case_number(search_input)
            
            # Search and get first link
            case_url = self.search_and_get_first_link(search_term, case_number_only)
            
            if not case_url:
                print("\nCould not find case using Google search.")
                print("This might be due to:")
                print("  - Google blocking automated searches")
                print("  - Case number doesn't exist")
                print("  - Network issues")
                print("\nTry:")
                print(f"  1. Run with --show-browser to see what's happening")
                print(f"  2. Search manually on lawphil.net and use --url option")
                print(f"  3. Check your internet connection")
                return False
            
            # Download the case as PDF
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
    
    def download_single_case(self, search_input, output_filename=None):
        """Download a single case (opens and closes browser)."""
        try:
            self.setup_driver()
            return self.download_case(search_input, output_filename)
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
    
    # Create downloader
    downloader = LawPhilDownloader(headless=not args.show_browser)
    
    # Download case
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
