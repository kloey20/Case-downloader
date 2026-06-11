#!/usr/bin/env python3
"""
LawPhil Case Downloader - Edge Only / Absolute Path Version
"""

import sys
import re
import os
from datetime import datetime
import time

try:
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options
    from selenium.webdriver.common.by import By
except ImportError:
    print("Error: Selenium not installed.")
    print("Please run: pip install selenium")
    sys.exit(1)


class LawPhilDownloader:
    SEARCH_URL = "https://www.google.com/search?q=site:lawphil.net+"
    
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        
    def setup_driver(self):
        edge_options = Options()
        
        if self.headless:
            edge_options.add_argument('--headless=new')
        
        edge_options.add_argument('--no-sandbox')
        edge_options.add_argument('--disable-dev-shm-usage')
        edge_options.add_argument('--disable-gpu')
        edge_options.add_argument('--disable-blink-features=AutomationControlled')
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_experimental_option('useAutomationExtension', False)
        
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.cookie_controls_mode": 0
        }
        edge_options.add_experimental_option("prefs", prefs)
        
        try:
            self.driver = webdriver.Edge(options=edge_options)
        except Exception as e:
            raise
    
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
        
        self.case_number_only = case_number_only
        self.driver.get(search_url)
        time.sleep(3) 
        
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href]")
            for link in links:
                href = link.get_attribute('href')
                if href and 'lawphil.net' in href and 'judjuris' in href and '.html' in href:
                    if not href.startswith('https://www.google.com'):
                        return href
            return None
        except Exception:
            return None
    
    def close_popups_and_accept_cookies(self):
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
                            time.sleep(0.5)
                            break
                except:
                    continue
            
            overlay_selectors = ["[class*='modal']", "[class*='overlay']", "[class*='popup']", "[id*='modal']", "[id*='overlay']", "[id*='popup']"]
            for selector in overlay_selectors:
                try:
                    overlays = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for overlay in overlays:
                        if overlay.is_displayed():
                            close_buttons = overlay.find_elements(By.CSS_SELECTOR, "button[class*='close'], a[class*='close'], [aria-label*='close'], [title*='close']")
                            for btn in close_buttons:
                                try:
                                    btn.click()
                                    time.sleep(0.5)
                                    break
                                except:
                                    continue
                except:
                    continue
        except Exception:
            pass
    
    def save_page_as_pdf(self, url, output_filename=None):
        if not url:
            return None
        
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
                
            # Detect exact location of the running .exe or script
            if getattr(sys, 'frozen', False):
                # We are running as a PyInstaller .exe
                base_dir = os.path.dirname(sys.executable)
            else:
                # We are running as a standard Python script
                base_dir = os.path.dirname(os.path.abspath(__file__))
                
            # Combine the .exe folder with the generated filename
            abs_path = os.path.join(base_dir, output_filename)
            
            import base64
            pdf_settings = {
                "landscape": False, "displayHeaderFooter": False, "printBackground": True,
                "preferCSSPageSize": False, "paperWidth": 8.27, "paperHeight": 11.69,
                "marginTop": 0.4, "marginBottom": 0.4, "marginLeft": 0.4, "marginRight": 0.4,
            }
            
            result = self.driver.execute_cdp_cmd("Page.printToPDF", pdf_settings)
            
            # Save the file directly to the guaranteed path
            with open(abs_path, 'wb') as f:
                f.write(base64.b64decode(result['data']))
            
            return abs_path
            
        except Exception as e:
            print(f"✗ Error saving PDF: {e}")
            return None
    
    def download_case(self, search_input, output_filename=None):
        try:
            self.setup_driver()
            search_term, case_number_only = self.format_case_number(search_input)
            case_url = self.search_and_get_first_link(search_term, case_number_only)
            if not case_url:
                return None
            return self.save_page_as_pdf(case_url, output_filename)
        finally:
            if self.driver:
                self.driver.quit()