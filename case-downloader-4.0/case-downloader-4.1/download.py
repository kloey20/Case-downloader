#!/usr/bin/env python3
"""
LawPhil Case Downloader - Surgical CSS Cleanup Version
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
            
    # ==========================================
    # CLEANUP PHASE 1: Popups & Cookies
    # ==========================================
    def destroy_cookie_banners(self):
        try:
            WebDriverWait(self.driver, 1).until(EC.alert_is_present())
            self.driver.switch_to.alert.accept()
        except:
            pass

        try:
            js_nuke_cookies = """
            var btns = document.querySelectorAll('button, a, div');
            var keywords = ['ok', 'accept', 'agree', 'got it', 'close'];
            for (var i = 0; i < btns.length; i++) {
                var txt = btns[i].innerText ? btns[i].innerText.toLowerCase().trim() : '';
                if (keywords.includes(txt)) {
                    btns[i].click();
                }
            }
            
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
            time.sleep(0.5)
        except Exception:
            pass

    # ==========================================
    # CLEANUP PHASE 2: Surgical CSS Hiding
    # ==========================================
    def format_and_clean_document(self):
        """Uses CSS to selectively turn off bad elements without breaking the DOM structure."""
        try:
            js_clean_document = """
            // 1. Globally remove hardcoded background colors and images from HTML tags
            document.querySelectorAll('*').forEach(el => {
                if (el.hasAttribute('background')) el.removeAttribute('background');
                if (el.hasAttribute('bgcolor')) el.removeAttribute('bgcolor');
            });

            // 2. Inject a surgical stylesheet to hide everything we don't want
            const style = document.createElement('style');
            style.innerHTML = `
                /* Hide LawPhil's external graphics and top banners */
                img[src*="back.gif"], img[src*="top.gif"], img[src*="010.gif"],
                img[src*="008.jpg"], img[src*="009.jpg"], img[src*="lawphil.jpg"],
                img[src*="home.png"], img[src*="alf.png"] {
                    display: none !important;
                }

                /* Hide the navigation menu and search bars at the top */
                .menuBar, .level0, .level1, form, .gsc-control-searchbox-only {
                    display: none !important;
                }

                /* Hide all horizontal lines */
                hr {
                    display: none !important;
                }

                /* Hide specific 'back' and 'top' link actions */
                a[href*="history.back"], a[href*="#top"] {
                    display: none !important;
                }

                /* Hide the specific class LawPhil uses for the Arellano Law footer */
                a.id, .id {
                    display: none !important;
                }

                /* Lock the layout, background, and typography for a clean PDF */
                html, body { 
                    background-color: #ffffff !important; 
                    background-image: none !important;
                    color: #000000 !important; 
                    font-family: 'Times New Roman', Times, serif !important; 
                    font-size: 12pt !important; 
                    line-height: 1.5 !important; 
                }
                
                table, tr, td, center, div { 
                    background-color: transparent !important; 
                    background-image: none !important; 
                }
                
                p, blockquote { 
                    text-align: justify !important; 
                }
                
                center, p[align="center"] { 
                    text-align: center !important; 
                }
            `;
            document.head.appendChild(style);

            // 3. Fallback: Find exact text nodes for footer text and hide just the text (not the container)
            document.querySelectorAll('a, span, p, div, center').forEach(el => {
                const txt = el.innerText ? el.innerText.toLowerCase().trim() : '';
                if (txt === 'back' || txt === 'top' || txt === 'back to top' || 
                    txt.includes('arellano law foundation') || txt.includes('the lawphil project')) {
                    el.style.display = 'none';
                }
            });
            """
            self.driver.execute_script(js_clean_document)
            time.sleep(0.5)
        except Exception as js_err:
            print(f"Notice: Phase 2 Cleanup adjustments skipped ({js_err})")

    # ==========================================
    # MAIN WORKFLOW
    # ==========================================
    def process_and_download(self, search_input, output_dir=None):
        try:
            self.setup_driver()
            
            search_term, case_number_only = self.format_case_number(search_input)
            search_query = search_term.replace(" ", "+")
            self.driver.get(f"{self.SEARCH_URL}{search_query}")
            time.sleep(2) 
            
            case_url = None
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href]")
            for link in links:
                href = link.get_attribute('href')
                if href and 'lawphil.net' in href and 'judjuris' in href and '.html' in href:
                    if not href.startswith('https://www.google.com'):
                        case_url = href
                        break
            
            if not case_url:
                return None
                
            self.driver.get(case_url)
            time.sleep(2) 
            
            self.destroy_cookie_banners()
            self.format_and_clean_document()
            
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