#!/usr/bin/env python3
"""
LawPhil Case Downloader - Auto-Queue & Aggressive Cookie Blocking

This version removes LawPhil's visible site chrome before printing to PDF:
- cookie popups / sticky banners
- top navigation/header rows
- bottom navigation/footer blocks such as Back, Top, and LawPhil credits
"""

import base64
import os
import re
import sys
import time
from urllib.parse import quote_plus

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
            edge_options.add_argument("--headless=new")
        edge_options.add_argument("--no-sandbox")
        edge_options.add_argument("--disable-dev-shm-usage")
        edge_options.add_argument("--disable-gpu")
        edge_options.add_argument("--disable-blink-features=AutomationControlled")
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_experimental_option("useAutomationExtension", False)

        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.cookie_controls_mode": 0,
        }
        edge_options.add_experimental_option("prefs", prefs)
        self.driver = webdriver.Edge(options=edge_options)

    def format_case_number(self, case_input):
        case_input = case_input.strip()
        if case_input.isdigit():
            return f"G.R. No. {case_input}", case_input

        match = re.search(r"(\d+)", case_input)
        number_only = match.group(1) if match else case_input
        return case_input, number_only

    def destroy_cookie_banners(self):
        """Remove cookie popups and sticky cookie notices before printing."""
        try:
            WebDriverWait(self.driver, 1).until(EC.alert_is_present())
            self.driver.switch_to.alert.accept()
        except Exception:
            pass

        try:
            js_nuke_cookies = r"""
            (function () {
                const keywords = ['ok', 'accept', 'agree', 'got it', 'close'];

                document.querySelectorAll('button, a, div').forEach(el => {
                    const txt = (el.innerText || '').toLowerCase().trim();
                    if (keywords.includes(txt)) {
                        el.click();
                    }
                });

                document.querySelectorAll('*').forEach(el => {
                    const style = window.getComputedStyle(el);
                    const txt = (el.innerText || '').toLowerCase();
                    if ((style.position === 'fixed' || style.position === 'sticky') && txt.includes('cookie')) {
                        el.style.setProperty('display', 'none', 'important');
                        el.style.setProperty('opacity', '0', 'important');
                    }
                });
            })();
            """
            self.driver.execute_script(js_nuke_cookies)
            time.sleep(0.5)
        except Exception:
            pass

    def clean_lawphil_page_for_pdf(self):
        """
        Hide LawPhil's page chrome before Page.printToPDF runs.

        The footer cleanup is intentionally conservative: it removes only footer-like
        blocks near the bottom of the document, or blocks whose content/attributes are
        navigation-only, such as Back, Top, Home, LawPhil Project, or Arellano credits.
        This prevents ordinary judgment text containing words like "back" or "top"
        from being removed.
        """
        self.destroy_cookie_banners()

        js_clean_page = r"""
        (function () {
            const HIDE = 'none';

            function hide(el) {
                if (!el || !el.style) return;
                el.style.setProperty('display', HIDE, 'important');
                el.setAttribute('data-lawphil-hidden-for-pdf', 'true');
            }

            function remove(el) {
                if (el && el.parentNode) {
                    el.parentNode.removeChild(el);
                }
            }

            function normalizeText(value) {
                return (value || '').replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
            }

            function elementText(el) {
                return normalizeText(el ? (el.innerText || el.textContent || '') : '');
            }

            function attrText(el) {
                if (!el) return '';
                const attrs = ['href', 'src', 'alt', 'title', 'aria-label', 'name', 'id', 'class'];
                return attrs.map(attr => el.getAttribute(attr) || '').join(' ');
            }

            function pageY(el) {
                const rect = el.getBoundingClientRect();
                return rect.top + (window.scrollY || window.pageYOffset || 0);
            }

            function isLowerPartOfPage(el) {
                const doc = document.documentElement;
                const height = Math.max(
                    doc.scrollHeight,
                    document.body ? document.body.scrollHeight : 0,
                    window.innerHeight || 0
                );

                // Allow short pages to still be cleaned, but protect the top header.
                return pageY(el) > Math.min(height * 0.45, Math.max(height - 900, 0));
            }

            function wordCount(text) {
                if (!text) return 0;
                return text.split(/\s+/).filter(Boolean).length;
            }

            function isFooterText(text) {
                const lower = normalizeText(text).toLowerCase();
                if (!lower) return false;

                return (
                    lower.includes('the lawphil project') ||
                    lower.includes('arellano law foundation') ||
                    /^(back|top|home|previous|next|return|go to top)$/i.test(lower) ||
                    /^(back\s+top|top\s+back|home\s+top)$/i.test(lower) ||
                    /^\*\s*\*\s*\*$/.test(lower)
                );
            }

            function hasFooterNavigationAttrs(el) {
                const text = elementText(el);
                const attrs = attrText(el);
                const haystack = normalizeText(text + ' ' + attrs).toLowerCase();
                if (!haystack) return false;

                const tag = el && el.tagName ? el.tagName.toLowerCase() : '';
                const hasImage = tag === 'img' || Boolean(el.querySelector && el.querySelector('img'));
                const isShortBrandBlock = wordCount(text) <= 12 && /lawphil|arellano/i.test(haystack);

                return (
                    /(^|[\/_\-.#?=&\s])(back|top|home|previous|next)([\/_\-.#?=&\s]|$)/i.test(haystack) ||
                    haystack.includes('#top') ||
                    (hasImage && isShortBrandBlock) ||
                    isFooterText(text)
                );
            }

            function nearestSmallContainer(el) {
                let node = el;

                while (node && node !== document.body && node !== document.documentElement) {
                    const tag = node.tagName ? node.tagName.toLowerCase() : '';
                    const text = elementText(node);
                    const words = wordCount(text);
                    const links = node.querySelectorAll ? node.querySelectorAll('a').length : 0;
                    const images = node.querySelectorAll ? node.querySelectorAll('img').length : 0;

                    if (
                        ['p', 'center', 'div', 'td', 'tr', 'table', 'font'].includes(tag) &&
                        words <= 25 &&
                        (isFooterText(text) || links > 0 || images > 0 || hasFooterNavigationAttrs(node))
                    ) {
                        return node;
                    }

                    node = node.parentElement;
                }

                return el;
            }

            function removeNodeAndFollowingSiblings(node) {
                if (!node || !node.parentNode) return;

                let current = node;
                while (current) {
                    const next = current.nextSibling;
                    remove(current);
                    current = next;
                }
            }

            function removeFromFooterMarker(root) {
                if (!root) return;

                const markers = Array.from(root.querySelectorAll('p, center, div, table, tr, td, font, span'));
                for (const marker of markers) {
                    const text = elementText(marker);
                    if (isLowerPartOfPage(marker) && /the lawphil project|arellano law foundation/i.test(text)) {
                        const container = nearestSmallContainer(marker);
                        removeNodeAndFollowingSiblings(container);
                        return;
                    }
                }
            }

            function removeFooterNavigation(root) {
                if (!root) return;

                // First remove everything from the known LawPhil footer credit onward.
                removeFromFooterMarker(root);

                // Then remove any remaining bottom-only Back/Top/Home image/link blocks.
                Array.from(root.querySelectorAll('a, img')).forEach(el => {
                    if (!isLowerPartOfPage(el)) return;
                    if (!hasFooterNavigationAttrs(el)) return;

                    const container = nearestSmallContainer(el);
                    remove(container);
                });

                // Finally prune empty or asterisk-only trailing blocks left behind by the footer removal.
                const candidates = Array.from(root.querySelectorAll('p, center, div, td, tr, table'));
                candidates.reverse().forEach(el => {
                    if (!isLowerPartOfPage(el)) return;
                    const text = elementText(el);
                    const hasMedia = el.querySelector && el.querySelector('img, svg, canvas, iframe, object, embed');
                    const hasForm = el.querySelector && el.querySelector('input, textarea, select, button');
                    if (!hasMedia && !hasForm && (text === '' || isFooterText(text))) {
                        remove(el);
                    }
                });
            }

            // 1. Hide independent navigation elements, sidebars, search forms, and menu rows.
            const navigationSelectors = [
                '.level0', '.level1', '.top', '#NuMainContainer',
                'form', '.gstl_50', '#gs_id50', 'nav', 'header'
            ];
            navigationSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(hide);
            });

            // 2. Hide top visual rows inside LawPhil's legacy layout tables.
            const blockquote = document.querySelector('blockquote');
            if (blockquote) {
                const mainContentRow = blockquote.closest('tr');
                if (mainContentRow) {
                    let priorRow = mainContentRow.previousElementSibling;
                    while (priorRow) {
                        hide(priorRow);
                        priorRow = priorRow.previousElementSibling;
                    }
                }
            }

            // 3. Remove bottom footer/navigation blocks before printToPDF.
            removeFooterNavigation(blockquote || document.body);

            // 4. Also remove layout rows after the main content row when LawPhil puts
            //    footer navigation outside the blockquote.
            if (blockquote) {
                const mainContentRow = blockquote.closest('tr');
                if (mainContentRow) {
                    let nextRow = mainContentRow.nextElementSibling;
                    while (nextRow) {
                        const following = nextRow.nextElementSibling;
                        const text = elementText(nextRow);
                        if (isFooterText(text) || hasFooterNavigationAttrs(nextRow) || wordCount(text) <= 30) {
                            hide(nextRow);
                        }
                        nextRow = following;
                    }
                }
            }

            // 5. Add print CSS so any dynamically inserted Back/Top controls stay hidden.
            const style = document.createElement('style');
            style.setAttribute('data-lawphil-pdf-cleanup', 'true');
            style.textContent = `
                @media print {
                    [data-lawphil-hidden-for-pdf="true"],
                    a[href="#top"],
                    a[href*="back" i],
                    a[href*="top" i],
                    img[src*="back" i],
                    img[src*="top" i],
                    img[alt*="back" i],
                    img[alt*="top" i] {
                        display: none !important;
                        visibility: hidden !important;
                    }
                }
            `;
            document.head.appendChild(style);
        })();
        """

        try:
            self.driver.execute_script(js_clean_page)
            time.sleep(0.5)
        except Exception as js_err:
            print(f"Notice: Optional page cleanup skipped ({js_err})")

    def process_and_download(self, search_input, output_dir=None):
        """Search, navigate, clean the page, and save the decision as a PDF."""
        try:
            self.setup_driver()

            # Phase 1: Format and search.
            search_term, case_number_only = self.format_case_number(search_input)
            search_query = quote_plus(search_term)
            self.driver.get(f"{self.SEARCH_URL}{search_query}")
            time.sleep(2)

            # Phase 2: Find the first LawPhil jurisprudence HTML result.
            case_url = None
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href]")
            for link in links:
                href = link.get_attribute("href")
                if href and "lawphil.net" in href and "judjuris" in href and ".html" in href:
                    if not href.startswith("https://www.google.com"):
                        case_url = href
                        break

            if not case_url:
                return None

            # Phase 3: Navigate to the case and clean headers/footers before printing.
            self.driver.get(case_url)
            time.sleep(2)
            self.clean_lawphil_page_for_pdf()

            # Phase 4: Save PDF.
            output_filename = f"G.R. No. {case_number_only}.pdf"

            if output_dir and os.path.isdir(output_dir):
                base_dir = output_dir
            else:
                if getattr(sys, "frozen", False):
                    base_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))

            abs_path = os.path.join(base_dir, output_filename)

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

            with open(abs_path, "wb") as f:
                f.write(base64.b64decode(result["data"]))

            return abs_path

        except Exception as e:
            print(f"Error: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()
