#!/usr/bin/env python3
"""
LawPhil Case Downloader - Auto-Queue & Aggressive Cookie Blocking
"""

import sys
import re
import os
import time

try:
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    print("Error: Selenium not installed.")
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
        
        prefs = {"profile.default_content_setting_values.notifications": 2, "profile.cookie_controls_mode": 0}
        edge_options.add_experimental_option("prefs", prefs)
        self.driver = webdriver.Edge(options=edge_options)
    
    def format_case_number(self, case_input):
        case_input = case_input.strip()
        if case_input.isdigit():
            return f"G.R. No. {case_input}", case_input
        else:
            match = re.search(r'(\d+)', case_input)
            number_only = match.group(1) if match else case_input
            return case_input, number_only
            
    def destroy_cookie_banners(self):
        """Aggressively removes cookie popups using Javascript and handles alerts."""
        # 1. Handle native browser alerts (if any)
        try:
            WebDriverWait(self.driver, 1).until(EC.alert_is_present())
            self.driver.switch_to.alert.accept()
        except:
            pass

        # 2. Inject Javascript to forcefully click OK and hide sticky cookie banners
        try:
            js_nuke_cookies = """
            // Try clicking anything that looks like an OK/Accept button
            var btns = document.querySelectorAll('button, a, div');
            var keywords = ['ok', 'accept', 'agree', 'got it', 'close'];
            for (var i = 0; i < btns.length; i++) {
                var txt = btns[i].innerText ? btns[i].innerText.toLowerCase().trim() : '';
                if (keywords.includes(txt)) {
                    btns[i].click();
                }
            }
            
            // Forcefully hide any fixed/sticky elements at the bottom or top of the screen
            var elements = document.querySelectorAll('*');
            for (var i = 0; i < elements.length; i++) {
                var style = window.getComputedStyle(elements[i]);
                if (style.position === 'fixed' || style.position === 'sticky') {
                    if (elements[i].innerText && elements[i].innerText.toLowerCase().includes('cookie')) {
                        elements[i].style.display = 'none';
                        elements[i].style.opacity = '0';
                    }
                }
            }
            """
            self.driver.execute_script(js_nuke_cookies)
            time.sleep(1) # Wait a second for animations to clear
        except Exception:
            pass

    def process_and_download(self, search_input, output_dir=None):
        """Searches, navigates, cleans the page, and auto-saves the PDF in one go."""
        try:
            self.setup_driver()
            
            # Phase 1: Format and Search
            search_term, case_number_only = self.format_case_number(search_input)
            search_query = search_term.replace(" ", "+")
            self.driver.get(f"{self.SEARCH_URL}{search_query}")
            time.sleep(2) 
            
            # Phase 2: Find Link
            case_url = None
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href]")
            for link in links:
                href = link.get_attribute('href')
                if href and 'lawphil.net' in href and 'judjuris' in href and '.html' in href:
                    if not href.startswith('https://www.google.com'):
                        case_url = href
                        break
            
            if not case_url:
                return None # Case not found
                
            # Phase 3: Navigate and Clean Page
            self.driver.get(case_url)
            time.sleep(2) 
            self.destroy_cookie_banners()
            
            # === NEW ADDITION: HIDE LAWPHIL HEADER BANNER WITHOUT BREAKING HTML ===
            try:
                js_clean_headers = """
                // 1. Hide independent navigation elements, sidebars, and search frames
                const navigationSelectors = ['.level0', '.level1', '.top', '#NuMainContainer', 'form', '.gstl_50', '#gs_id50'];
                navigationSelectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => el.style.display = 'none');
                });

                // 2. Hide top visual header rows inside the layout table, keeping structural elements safe
                const blockquote = document.querySelector('blockquote');
                if (blockquote) {
                    const mainContentRow = blockquote.closest('tr');
                    if (mainContentRow) {
                        let priorRow = mainContentRow.previousElementSibling;
                        while (priorRow) {
                            priorRow.style.display = 'none';
                            priorRow = priorRow.previousElementSibling;
                        }
                    }
                }
                """
                self.driver.execute_script(js_clean_headers)
                time.sleep(0.5) # Brief pause to allow DOM elements to hide smoothly
            except Exception as js_err:
                print(f"Notice: Optional page cleanup layout skipped ({js_err})")
            # ======================================================================
            
            # Phase 4: Save PDF
            output_filename = f"G.R. No. {case_number_only}.pdf"
            
            if output_dir and os.path.isdir(output_dir):
                base_dir = output_dir
            else:
                if getattr(sys, 'frozen', False):
                    base_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    
            abs_path = os.path.join(base_dir, output_filename)
            
            import base64
            pdf_settings = {
                "landscape": False, "displayHeaderFooter": False, "printBackground": True,
                "preferCSSPageSize": False, "paperWidth": 8.27, "paperHeight": 11.69,
                "marginTop": 0.4, "marginBottom": 0.4, "marginLeft": 0.4, "marginRight": 0.4,
            }
            
            result = self.driver.execute_cdp_cmd("Page.printToPDF", pdf_settings)
            
            with open(abs_path, 'wb') as f:
                f.write(base64.b64decode(result['data']))
                
            return abs_path
            
        except Exception as e:
            print(f"✗ Error: {e}")
            return None
        finally:
            if self.driver: 
                self.driver.quit()