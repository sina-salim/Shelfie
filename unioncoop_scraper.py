import logging
import os
import re
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import pandas as pd
import traceback
from webdriver_manager.chrome import ChromeDriverManager

# تنظیم لاگر
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("unioncoop_scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UnionCoopMultiPageScraper:
    """
    کلاس برای استخراج محصولات از وبسایت Union Coop
    """
    
    def __init__(self, url, max_pages=None):
        """
        مقداردهی اولیه کلاس
        
        پارامترها:
            url (str): آدرس وب‌سایت برای استخراج محصولات
            max_pages (int, optional): حداکثر تعداد صفحاتی که باید استخراج شود. اگر None باشد، همه صفحات استخراج می‌شوند.
        """
        self.url = url
        self.max_pages = max_pages
        self.products = []
        logger.info(f"Union Coop Scraper initialized with URL: {url}")
        if max_pages:
            logger.info(f"Maximum pages to scrape: {max_pages}")
        else:
            logger.info("Scraping all available pages")
    
    def setup_driver(self):
        """
        راه‌اندازی درایور سلنیوم
        
        Returns:
            webdriver: آبجکت درایور سلنیوم
        """
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            logger.info("Chrome WebDriver setup successfully")
            return driver
        except Exception as e:
            logger.error(f"Error setting up Chrome WebDriver: {e}")
            raise
    
    def get_total_products_and_pages(self, driver):
        """
        تعیین تعداد کل صفحات برای استخراج
        
        پارامترها:
            driver (webdriver): آبجکت درایور سلنیوم
            
        Returns:
            int: تعداد کل صفحات
        """
        try:
            # صفحه اول را لود می‌کنیم
            logger.info(f"Loading URL to get total pages: {self.url}")
            driver.get(self.url)
            time.sleep(5)  # زمان بیشتر برای لود شدن صفحه
            
            try:
                # یافتن لینک صفحه آخر - ابتدا با سلکتور دقیق
                pagination_selectors = [
                    ".ais-Pagination-list", 
                    ".ais-Pagination-item",
                    ".pages",
                    ".pagination"
                ]
                
                pagination = None
                for selector in pagination_selectors:
                    try:
                        pagination = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        logger.info(f"Found pagination with selector: {selector}")
                        break
                    except (TimeoutException, NoSuchElementException):
                        continue
                
                if pagination:
                    # تلاش برای یافتن لینک "Next page"
                    next_page_selectors = [
                        ".ais-Pagination-item--nextPage",
                        "a[aria-label='Next']",
                        ".next-page"
                    ]
                    
                    next_page_li = None
                    for selector in next_page_selectors:
                        try:
                            next_page_li = driver.find_element(By.CSS_SELECTOR, selector)
                            break
                        except NoSuchElementException:
                            continue
                    
                    if next_page_li:
                        # پیدا کردن المان قبل از "Next page" که آخرین صفحه است
                        try:
                            last_page_li = next_page_li.find_element(By.XPATH, "preceding-sibling::li[1]")
                            last_page_link = last_page_li.find_element(By.TAG_NAME, "a")
                            last_page_number = int(last_page_link.text)
                            logger.info(f"Total pages found: {last_page_number}")
                            return last_page_number
                        except (NoSuchElementException, ValueError):
                            # اگر نتوانستیم المان قبلی را پیدا کنیم یا متن آن به عدد تبدیل نشد
                            pass
                
                # روش جایگزین: جستجوی مستقیم برای آخرین شماره صفحه
                try:
                    page_items = driver.find_elements(By.CSS_SELECTOR, ".ais-Pagination-item--page")
                    if page_items:
                        last_page_text = page_items[-1].text.strip()
                        last_page_number = int(last_page_text)
                        logger.info(f"Total pages found (alternative method): {last_page_number}")
                        return last_page_number
                except (NoSuchElementException, ValueError, IndexError):
                    pass
                    
                # روش جایگزین 2: بررسی URL صفحات در HTML
                try:
                    html_content = driver.page_source
                    # جستجوی الگوی صفحه‌بندی در HTML
                    pagination_patterns = [
                        r'page=(\d+)',
                        r'Pagination.*?(\d+).*?Next page'
                    ]
                    
                    for pattern in pagination_patterns:
                        matches = re.findall(pattern, html_content)
                        if matches:
                            # تبدیل همه اعداد یافت شده به عدد صحیح و یافتن بزرگترین
                            page_numbers = [int(match) for match in matches if match.isdigit()]
                            if page_numbers:
                                max_page = max(page_numbers)
                                logger.info(f"Total pages found (HTML pattern method): {max_page}")
                                return max_page
                except Exception as e:
                    logger.warning(f"Error while parsing HTML for page numbers: {e}")
                
                # برای آزمایش، تعداد صفحات را 3 در نظر می‌گیریم
                logger.warning("Could not determine last page number, using default of 3")
                return 3
                            
            except (NoSuchElementException, TimeoutException) as e:
                logger.warning(f"Could not find pagination or last page element: {e}")
                logger.info("Assuming only one page is available")
                return 1
                
        except Exception as e:
            logger.error(f"Error determining total pages: {e}")
            logger.info("Falling back to default of 1 page")
            return 1
    
    def scrape_page(self, driver, page_url):
        """
        استخراج محصولات از یک صفحه
        
        پارامترها:
            driver (webdriver): آبجکت درایور سلنیوم
            page_url (str): آدرس صفحه برای استخراج
            
        Returns:
            list: لیست محصولات استخراج شده از صفحه
        """
        try:
            logger.info(f"Loading page URL: {page_url}")
            driver.get(page_url)
            
            # منتظر شدن برای لود شدن محصولات (تغییر سلکتور به سلکتور صحیح)
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.result"))
                )
            except TimeoutException:
                # تلاش با سلکتور دیگر در صورت شکست
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".result-title"))
                    )
                except TimeoutException:
                    logger.warning("Could not find product elements with standard selectors, trying alternate selectors")
                    # تلاش با انتظار برای لود شدن هر نوع محتوا
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
            
            # زمان اضافی برای اطمینان از لود کامل همه محتوا
            time.sleep(5)
            
            # اسکرول به پایین صفحه برای لود شدن همه محصولات
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            # تلاش برای یافتن محصولات با سلکتورهای مختلف
            product_elements = []
            selectors_to_try = [
                "a.result", 
                ".result", 
                "div.hit", 
                ".ais-hits--item",
                ".product-item"
            ]
            
            for selector in selectors_to_try:
                product_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if product_elements:
                    logger.info(f"Found {len(product_elements)} product elements using selector: {selector}")
                    break
            
            if not product_elements:
                logger.warning("No product elements found with any selector")
                # ذخیره HTML صفحه برای دیباگ
                with open("unioncoop_debug.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                logger.info("Saved page HTML to unioncoop_debug.html for debugging")
                return []
            
            page_products = []
            success_count = 0
            fail_count = 0
            
            for product in product_elements:
                try:
                    # تلاش برای استخراج نام محصول با سلکتورهای مختلف
                    name = ""
                    name_selectors = ["h3.result-title", ".result-title", "h3", "a.name", ".product-name"]
                    for selector in name_selectors:
                        try:
                            name_element = product.find_element(By.CSS_SELECTOR, selector)
                            name = name_element.text.strip()
                            if name:
                                break
                        except NoSuchElementException:
                            continue
                    
                    if not name:
                        # اگر نام پیدا نشد، به محصول بعدی برو
                        logger.warning("Could not find product name, skipping product")
                        fail_count += 1
                        continue
                    
                    # استخراج قیمت (قیمت با تخفیف)
                    current_price = "N/A"
                    price_selectors = [
                        ".tamayaz.after_special.promotion", 
                        ".tamayaz", 
                        ".price", 
                        ".price-currency-symbol",
                        ".special-price",
                        ".product-price"
                    ]
                    
                    for selector in price_selectors:
                        try:
                            price_element = product.find_element(By.CSS_SELECTOR, selector)
                            price_text = price_element.text.strip()
                            # حذف "AED" یا دیگر پیشوندها از قیمت
                            price_text = re.sub(r'[^\d.]', '', price_text)
                            if price_text:
                                # رفع مشکل تکرار قیمت‌ها
                                if len(price_text) % 2 == 0:
                                    mid_point = len(price_text) // 2
                                    first_half = price_text[:mid_point]
                                    second_half = price_text[mid_point:]
                                    # بررسی اگر دو نیمه مشابه هستند
                                    if first_half == second_half:
                                        price_text = first_half
                                
                                current_price = f"{price_text} AED"
                                break
                        except NoSuchElementException:
                            continue
                    
                    # استخراج وزن محصول (اگر در نام باشد)
                    weight = self._extract_weight(name)
                    
                    # استخراج برند محصول و حذف آن از نام محصول
                    brand, clean_name = self._extract_brand(name)
                    
                    # حذف وزن از نام محصول
                    clean_name = self._remove_weight_from_name(clean_name, weight)
                    
                    # ساخت دیکشنری محصول
                    product_data = {
                        "name": clean_name,
                        "brand": brand,
                        "price": current_price,
                        "weight": weight,
                        "store": "Union Coop"
                    }
                    
                    page_products.append(product_data)
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error extracting product: {e}")
                    logger.error(traceback.format_exc())
                    fail_count += 1
            
            logger.info(f"Successfully extracted {success_count} products, failed {fail_count}")
            return page_products
            
        except Exception as e:
            logger.error(f"Error scraping page {page_url}: {e}")
            logger.error(traceback.format_exc())
            return []
    
    def _extract_weight(self, product_name):
        """
        استخراج وزن محصول از نام آن
        
        پارامترها:
            product_name (str): نام محصول
            
        Returns:
            str: وزن محصول یا مقدار پیش‌فرض
        """
        # الگوهای مختلف برای استخراج وزن
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:kg|kilo|kilogram)s?',
            r'(\d+(?:\.\d+)?)\s*(?:g|gram)s?',
            r'(\d+(?:\.\d+)?)\s*(?:ml|milliliter)s?',
            r'(\d+(?:\.\d+)?)\s*(?:l|liter)s?',
            r'(\d+(?:\.\d+)?)(?:\s*x\s*\d+)?(?:\s*|-)(?:kg|g|ml|l)',
            r'(\d+(?:\.\d+)?)\s*(?:oz|ounce)s?',
            r'(\d+(?:\.\d+)?)\s*(?:lb|pound)s?',
            r'-\s*(\d+(?:\.\d+)?(?:\s*x\s*\d+)?(?:\s*|-)(?:kg|g|ml|l|oz|lb))'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, product_name, re.IGNORECASE)
            if match:
                return match.group(0)
        
        # اگر هیچ الگویی پیدا نشد
        return "N/A"
    
    def _extract_brand(self, product_name):
        """
        استخراج برند محصول از نام آن و حذف برند از نام محصول
        
        پارامترها:
            product_name (str): نام محصول
            
        Returns:
            tuple: (برند محصول, نام محصول بدون برند)
        """
        # لیست برندهای معروف
        known_brands = [
            "Trust", "Al Ain", "Emirates", "Almarai", "Al Rawabi", "Nido", 
            "Anchor", "Lurpak", "President", "Nadec", "Farm Fresh", "KDD",
            "Luna", "Rainbow", "Al Manar", "Puck", "Kraft", "Kiri", "Delmonte",
            "Heinz", "Americana", "Al Kabeer", "Sadia", "Dairy Queen", "Nestle",
            "Danone", "Arla", "Philadelphia", "Kingdom", "Milky Mist", "Amul"
        ]
        
        clean_name = product_name
        
        # بررسی اگر برند در نام محصول است
        for brand in known_brands:
            if brand.lower() in product_name.lower():
                # حذف برند از نام محصول
                clean_name = re.sub(re.escape(brand), '', product_name, flags=re.IGNORECASE).strip()
                # حذف کاراکترهای اضافی مانند فاصله و خط تیره در ابتدا
                clean_name = re.sub(r'^[\s\-]+', '', clean_name)
                return brand, clean_name
        
        # اگر برند شناخته شده نبود، کلمات اول نام را به عنوان برند در نظر می‌گیریم
        words = product_name.split()
        if len(words) >= 2:
            potential_brand = " ".join(words[:2])
            clean_name = " ".join(words[2:])
            return potential_brand, clean_name
        
        # اگر نام کوتاه باشد، کلمه اول را به عنوان برند در نظر می‌گیریم
        if len(words) > 0:
            return words[0], " ".join(words[1:])
        
        return "N/A", product_name
    
    def _remove_weight_from_name(self, product_name, weight):
        """
        حذف وزن از نام محصول
        
        پارامترها:
            product_name (str): نام محصول
            weight (str): وزن استخراج شده از نام محصول
            
        Returns:
            str: نام محصول بدون وزن
        """
        if weight != "N/A":
            # حذف وزن از نام محصول
            clean_name = re.sub(re.escape(weight), '', product_name, flags=re.IGNORECASE).strip()
            # حذف کاراکترهای اضافی مانند خط تیره و پرانتز
            clean_name = re.sub(r'[-\(\)]\s*$', '', clean_name).strip()
            clean_name = re.sub(r'^\s*[-\(\)]', '', clean_name).strip()
            
            # حذف عبارات متداول مربوط به وزن
            weight_terms = ['gm', 'gram', 'g', 'kg', 'kilos', 'kilo', 'ml', 'liter', 'l', 'oz', 'ounce', 'lb', 'pound']
            for term in weight_terms:
                clean_name = re.sub(r'\b' + re.escape(term) + r'\b', '', clean_name, flags=re.IGNORECASE).strip()
            
            return clean_name
        
        return product_name
    
    def scrape_all_pages(self):
        """
        استخراج محصولات از همه صفحات
        """
        driver = None
        try:
            driver = self.setup_driver()
            total_pages = self.get_total_products_and_pages(driver)
            
            # اگر حداکثر تعداد صفحات تنظیم شده باشد
            if self.max_pages and self.max_pages < total_pages:
                total_pages = self.max_pages
                logger.info(f"Limiting scraping to {total_pages} pages as per max_pages setting")
            
            for page_num in range(1, total_pages + 1):
                # ساخت URL صفحه
                if page_num == 1:
                    page_url = self.url
                else:
                    # فرمت صفحه‌بندی مشخص شده در unioncoop.txt
                    page_url = f"{self.url}?page={page_num}"
                
                logger.info(f"Scraping page {page_num} of {total_pages}: {page_url}")
                
                try:
                    page_products = self.scrape_page(driver, page_url)
                    self.products.extend(page_products)
                    
                except Exception as e:
                    logger.error(f"Error scraping page {page_num}: {e}")
                    logger.error(traceback.format_exc())
                
                # وقفه کوتاه بین درخواست‌ها
                if page_num < total_pages:
                    time.sleep(3)
            
            logger.info(f"Total products scraped: {len(self.products)}")
            
            # ذخیره نهایی فایل اکسل
            filename = self.save_to_excel()
            return filename
            
        except Exception as e:
            logger.error(f"Error during scraping all pages: {e}")
            logger.error(traceback.format_exc())
            
            # در صورت خطا، سعی می‌کنیم محصولات جمع‌آوری شده تا به اینجا را ذخیره کنیم
            if self.products:
                logger.info(f"Attempting to save {len(self.products)} products collected so far")
                return self.save_to_excel()
            return None
        finally:
            if driver:
                driver.quit()
                logger.info("WebDriver closed")
    
    def save_to_excel(self, df=None):
        """
        ذخیره محصولات در فایل اکسل
        
        پارامترها:
            df (DataFrame, optional): دیتافریم محصولات. اگر None باشد، از محصولات استخراج شده استفاده می‌شود.
            
        Returns:
            str: نام فایل اکسل ایجاد شده
        """
        try:
            if df is None:
                df = pd.DataFrame(self.products)
            
            if df.empty:
                logger.warning("No products to save to Excel")
                return None
            
            # ایجاد نام فایل با تاریخ و زمان (مشابه سایر اسکرپرها)
            current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"shelfie_unioncoop_products_{current_datetime}.xlsx"
            
            # ذخیره به اکسل با xlsxwriter مشابه دیگر اسکرپرها
            writer = pd.ExcelWriter(filename, engine='xlsxwriter')
            df.to_excel(writer, index=False, sheet_name='Products')
            
            # تنظیم عرض ستون‌ها
            workbook = writer.book
            worksheet = writer.sheets['Products']
            for i, col in enumerate(df.columns):
                column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, column_width)
            
            writer.close()
            logger.info(f"Products saved to Excel file: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error saving products to Excel: {e}")
            logger.error(traceback.format_exc())
            return None 