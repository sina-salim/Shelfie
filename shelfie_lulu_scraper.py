"""
Shelfie - استخراج‌کننده اطلاعات محصولات از وب‌سایت‌ها
این اسکریپت برای استخراج اطلاعات محصولات از وب‌سایت‌های مختلف طراحی شده است.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import random
import logging
import math
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
import argparse

# تنظیم لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("shelfie_lulu_scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ShelfieScraper:
    """
    کلاس اصلی برای استخراج اطلاعات محصولات از وب‌سایت‌ها
    """
    def __init__(self, base_url, max_pages=None):
        self.base_url = base_url.rstrip("/")  # حذف اسلش از انتهای URL در صورت وجود
        self.products = []
        self.total_pages = 1
        self.max_pages = max_pages  # تعداد صفحات تعیین شده توسط کاربر
        
    def get_total_products_and_pages(self, driver):
        """استخراج تعداد کل محصولات و محاسبه تعداد صفحات"""
        try:
            # روش 1: تلاش برای یافتن تعداد کل محصولات از متن صفحه
            page_text = driver.page_source
            
            # جستجوی الگوهایی که معمولاً تعداد کل محصولات را نشان می‌دهند
            patterns = [
                r'(\d+)\s*items', 
                r'(\d+)\s*products',
                r'total\s*:\s*(\d+)',
                r'showing\s*\d+\s*-\s*\d+\s*of\s*(\d+)',
                r'(\d+)\s*results',
                r'All Products\s*\(\s*(\d+)\s*\)'  # الگوی جدید بر اساس format.txt
            ]
            
            total_products = 0
            for pattern in patterns:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    potential_count = int(match.group(1))
                    if potential_count > total_products:
                        total_products = potential_count
            
            # روش جدید: استخراج آخرین شماره صفحه از HTML با بررسی عنصر پیجینیشن
            # طبق format.txt، دیو شماره آخرین صفحه همیشه قبل از دیو نشانگر است
            try:
                # پیدا کردن المان نشانگر صفحه بعدی (Next cursor)
                next_page_cursor = driver.find_element(By.XPATH, "//a[contains(., 'Next') or contains(., '>')]")
                
                # پیدا کردن همه المان‌های لینک صفحه قبل از المان نشانگر
                pagination_links = driver.find_elements(By.XPATH, "//li/a[contains(@href, 'page=')]")
                
                highest_page = 0
                for link in pagination_links:
                    try:
                        # استخراج شماره صفحه از href
                        href = link.get_attribute('href')
                        page_num_match = re.search(r'page=(\d+)', href)
                        if page_num_match:
                            page_num = int(page_num_match.group(1))
                            if page_num > highest_page:
                                highest_page = page_num
                    except:
                        continue
                
                if highest_page > 0:
                    logger.info(f"آخرین شماره صفحه پیدا شده: {highest_page}")
                    # محاسبه تعداد صفحات از روی آخرین شماره پیجینیشن
                    self.total_pages = highest_page
                    
                    # اگر تعداد محصولات هنوز تعیین نشده، آن را تخمین می‌زنیم
                    if total_products == 0:
                        # فرض می‌کنیم هر صفحه حدود 20 محصول دارد
                        total_products = self.total_pages * 20
                    
                    # اگر کاربر تعداد صفحات را مشخص کرده باشد، آن را اعمال می‌کنیم
                    if self.max_pages is not None:
                        self.total_pages = min(self.total_pages, self.max_pages)
                        logger.info(f"محدود کردن تعداد صفحات به {self.total_pages} (تعیین شده توسط کاربر)")
                    
                    return self.total_pages
            except Exception as e:
                logger.warning(f"خطا در استخراج آخرین شماره صفحه: {e}")
            
            # روش 2: تلاش برای یافتن عنصر حاوی تعداد کل محصولات
            if total_products == 0:
                # الگوهای مختلفی را امتحان می‌کنیم
                total_products_elements = driver.find_elements(By.CSS_SELECTOR, 
                    "[class*='total-results'], [class*='total-product'], .heading-title span, .product-count, [class*='product-total'], [class*='count']")
                
                for element in total_products_elements:
                    text = element.text.strip()
                    # جستجوی الگوی عدد در متن
                    matches = re.findall(r'\b(\d+)\b', text)
                    if matches:
                        # تبدیل بزرگترین عدد یافت شده به تعداد محصولات
                        potential_count = max([int(m) for m in matches])
                        if potential_count > total_products:
                            total_products = potential_count
            
            # روش 3: تلاش برای یافتن آخرین صفحه در پیجینیشن
            if total_products == 0:
                pagination_elements = driver.find_elements(By.CSS_SELECTOR, 
                    ".pagination a, [class*='paging'] a, [class*='pagination'] span, [class*='pagination'] button")
                
                highest_page = 0
                for element in pagination_elements:
                    text = element.text.strip()
                    if text.isdigit():
                        page_num = int(text)
                        if page_num > highest_page:
                            highest_page = page_num
                
                if highest_page > 0:
                    # اگر تعداد صفحات را پیدا کردیم، تخمین می‌زنیم که هر صفحه 20 محصول دارد
                    total_products = highest_page * 20
                    self.total_pages = highest_page
                    
                    # اگر کاربر تعداد صفحات را مشخص کرده باشد، آن را اعمال می‌کنیم
                    if self.max_pages is not None:
                        self.total_pages = min(self.total_pages, self.max_pages)
                        logger.info(f"محدود کردن تعداد صفحات به {self.total_pages} (تعیین شده توسط کاربر)")
                    
                    return self.total_pages
            
            # روش 4: شمارش تعداد محصولات در صفحه فعلی و تخمین کل
            if total_products == 0:
                # شمارش محصولات در صفحه فعلی
                product_elements = driver.find_elements(By.CSS_SELECTOR, "div.mb-2.flex.max-w-full.flex-col")
                
                # اگر با سلکتور اصلی محصولات پیدا نشد، از سلکتورهای دیگر استفاده می‌کنیم
                if not product_elements:
                    product_elements = driver.find_elements(By.CSS_SELECTOR, 
                        ".product-item, [class*='product-card'], [data-testid*='-']")
                
                # اگر هنوز محصولی پیدا نشده، هر المانی که احتمالاً محصول است را شمارش می‌کنیم
                if not product_elements:
                    product_elements = driver.find_elements(By.CSS_SELECTOR, 
                        "a[href*='/p/'], [class*='product'], [class*='item']")
                
                products_per_page = len(product_elements)
                
                # تلاش برای حرکت به صفحه آخر برای تخمین تعداد کل صفحات
                last_page_buttons = driver.find_elements(By.CSS_SELECTOR, 
                    "[class*='pagination'] a:last-child, [class*='pagination'] li:last-child a, [aria-label='Next page']")
                
                max_pagination_clicks = 5  # حداکثر 5 کلیک به سمت صفحات بعدی
                page_count = 1
                
                for _ in range(max_pagination_clicks):
                    if last_page_buttons and last_page_buttons[-1].is_displayed() and last_page_buttons[-1].is_enabled():
                        try:
                            last_page_buttons[-1].click()
                            time.sleep(2)  # صبر برای بارگذاری صفحه جدید
                            page_count += 1
                            
                            # دوباره دکمه صفحه بعد را پیدا می‌کنیم
                            last_page_buttons = driver.find_elements(By.CSS_SELECTOR, 
                                "[class*='pagination'] a:last-child, [class*='pagination'] li:last-child a, [aria-label='Next page']")
                        except:
                            break
                    else:
                        break
                
                # برگشت به صفحه اول
                driver.get(f"{self.base_url}/?page=1")
                time.sleep(2)
                
                # تخمین تعداد کل محصولات بر اساس تعداد صفحات شمارش شده
                # با فرض اینکه صفحه آخر هم مشابه صفحات دیگر محصول دارد
                if products_per_page > 0:
                    # حداقل باید 20 تا باشد (استاندارد لولو هایپرمارکت)
                    products_per_page = max(products_per_page, 20)
                    total_products = products_per_page * (page_count + 2)  # +2 برای اطمینان از پوشش همه صفحات
                    self.total_pages = page_count + 2
            
            # اگر هنوز تعداد محصولات پیدا نشده، مقدار پیش‌فرض استفاده می‌کنیم
            if total_products == 0:
                # پیش‌فرض: فرض می‌کنیم حداقل 100 محصول وجود دارد (5 صفحه)
                total_products = 100
                self.total_pages = 5
            else:
                # محاسبه تعداد صفحات (هر صفحه حداکثر 20 محصول دارد)
                self.total_pages = math.ceil(total_products / 20)
            
            # حداقل 5 صفحه را بررسی می‌کنیم تا مطمئن شویم همه محصولات را پوشش داده‌ایم
            # مگر اینکه کاربر تعداد صفحات کمتری را مشخص کرده باشد
            if self.max_pages is None or self.max_pages >= 5:
                self.total_pages = max(self.total_pages, 5)
            else:
                self.total_pages = min(self.total_pages, self.max_pages)
            
            logger.info(f"تعداد کل محصولات تخمینی: {total_products} و تعداد صفحات محاسبه شده: {self.total_pages}")
            
            return self.total_pages
            
        except Exception as e:
            logger.error(f"خطا در استخراج تعداد کل محصولات: {e}")
            # در صورت خطا، حداقل 10 صفحه را استخراج می‌کنیم، مگر اینکه کاربر تعداد کمتری را مشخص کرده باشد
            if self.max_pages is not None:
                return min(10, self.max_pages)
            return 10
    
    def scrape_page(self, driver, page_url):
        """استخراج محصولات از یک صفحه خاص"""
        try:
            logger.info(f"استخراج محصولات از صفحه: {page_url}")
            
            # بارگذاری صفحه
            driver.get(page_url)
            
            # انتظار برای بارگذاری محصولات
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.mb-2.flex.max-w-full.flex-col, a[data-testid*='-']"))
                )
            except TimeoutException:
                logger.warning(f"بارگذاری محصولات در صفحه {page_url} با تایم‌اوت مواجه شد")
            
            # اسکرول به پایین برای بارگذاری همه محصولات
            total_height = driver.execute_script("return document.body.scrollHeight")
            for i in range(1, 10):  # اسکرول تا 10 بار برای بارگذاری محتوای بیشتر
                driver.execute_script(f"window.scrollTo(0, {i * total_height / 10});")
                time.sleep(0.5)
            
            # صبر کنید تا همه محصولات بارگذاری شوند
            time.sleep(2)
            
            # استخراج HTML صفحه
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # یافتن همه محصولات با الگوی مشخص شده در format.txt
            product_elements = soup.select("div.mb-2.flex.max-w-full.flex-col")
            
            page_products = []
            
            logger.info(f"تعداد محصولات یافت شده در صفحه: {len(product_elements)}")
            
            # اگر محصولی با الگوی اصلی پیدا نشد، از الگوی جایگزین استفاده کنید
            if not product_elements:
                logger.info("الگوی اصلی محصولات یافت نشد، استفاده از الگوی جایگزین...")
                product_containers = soup.select(".product-item, [class*='product-card']")
                
                for container in product_containers:
                    try:
                        # استخراج نام محصول
                        product_name_elem = container.select_one("a[class*='name'], a[class*='title'], h3, h4")
                        if not product_name_elem:
                            continue
                            
                        product_name = product_name_elem.text.strip()
                        product_url = product_name_elem.get('href', '')
                        if product_url and not product_url.startswith('http'):
                            product_url = 'https://gcc.luluhypermarket.com' + product_url
                        
                        # استخراج قیمت
                        price_elem = container.select_one("span[class*='price'], div[class*='price']")
                        price = price_elem.text.strip() if price_elem else "N/A"
                        
                        # استخراج وزن از نام محصول
                        weight_match = re.search(r'\b\d+\s*(?:g|kg|ml|l|pcs)\b', product_name, re.IGNORECASE)
                        weight = weight_match.group(0) if weight_match else "N/A"
                        
                        # اضافه کردن به لیست محصولات صفحه
                        page_products.append({
                            'product': self._clean_product_name(product_name),
                            'brand': self._extract_brand(product_name),
                            'price': price,
                            'weight': weight,
                            'website': 'luluhypermarket.com',
                            'url': product_url,
                            'page': page_url
                        })
                        
                        logger.info(f"محصول استخراج شد: {product_name} - {price}")
                    except Exception as e:
                        logger.error(f"خطا در استخراج محصول با الگوی جایگزین: {e}")
            else:
                # استخراج محصولات با الگوی اصلی
                for product_elem in product_elements:
                    try:
                        # استخراج نام محصول (دقیقاً مطابق با فرمت)
                        product_link = product_elem.select_one("a[data-testid*='-']")
                        if not product_link:
                            continue
                            
                        product_name = product_link.text.strip()
                        product_url = product_link.get('href', '')
                        if product_url and not product_url.startswith('http'):
                            product_url = 'https://gcc.luluhypermarket.com' + product_url
                        
                        # استخراج قیمت
                        price_elem = product_elem.select_one("span[data-testid='product-price']")
                        price = price_elem.text.strip() if price_elem else "N/A"
                        
                        # استخراج وزن از نام محصول
                        weight_match = re.search(r'\b\d+\s*(?:g|kg|ml|l|pcs)\b', product_name, re.IGNORECASE)
                        weight = weight_match.group(0) if weight_match else "N/A"
                        
                        # اضافه کردن به لیست محصولات صفحه
                        page_products.append({
                            'product': self._clean_product_name(product_name),
                            'brand': self._extract_brand(product_name),
                            'price': price,
                            'weight': weight,
                            'website': 'luluhypermarket.com',
                            'url': product_url,
                            'page': page_url
                        })
                        
                        logger.info(f"محصول استخراج شد: {product_name} - {price}")
                    except Exception as e:
                        logger.error(f"خطا در استخراج محصول با الگوی اصلی: {e}")
            
            # در صورتی که تعداد محصولات کم باشد، سعی کنید با جستجوی عمیق‌تر
            if len(page_products) < 5:
                logger.info("تعداد محصولات کم است، جستجوی عمیق‌تر برای یافتن محصولات...")
                deep_search_products = self._deep_search_products(driver, page_url)
                page_products.extend(deep_search_products)
            
            logger.info(f"تعداد کل محصولات استخراج شده از صفحه {page_url}: {len(page_products)}")
            
            return page_products
            
        except Exception as e:
            logger.error(f"خطا در استخراج محصولات از صفحه {page_url}: {e}")
            return []
    
    def scrape_all_pages(self):
        """استخراج محصولات از تمام صفحات"""
        # تنظیم Selenium
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        try:
            # ابتدا صفحه اول را بارگذاری می‌کنیم تا تعداد کل صفحات را مشخص کنیم
            first_page_url = f"{self.base_url}/?page=1"
            driver.get(first_page_url)
            
            # انتظار برای بارگذاری صفحه
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # استخراج تعداد کل صفحات
            total_pages = self.get_total_products_and_pages(driver)
            
            # استخراج محصولات از هر صفحه
            for page_num in range(1, total_pages + 1):
                page_url = f"{self.base_url}/?page={page_num}"
                page_products = self.scrape_page(driver, page_url)
                self.products.extend(page_products)
                
                # بررسی کنیم که آیا به انتهای محصولات رسیده‌ایم یا خیر
                # اگر 3 صفحه متوالی محصولی نداشت، احتمالاً به انتها رسیده‌ایم
                if not page_products and page_num > 3:
                    if not self.scrape_page(driver, f"{self.base_url}/?page={page_num+1}") and \
                       not self.scrape_page(driver, f"{self.base_url}/?page={page_num+2}"):
                        logger.info(f"به نظر می‌رسد به انتهای محصولات در صفحه {page_num} رسیده‌ایم. استخراج متوقف می‌شود.")
                        break
                
                # اضافه کردن تاخیر بین صفحات برای جلوگیری از مسدود شدن
                if page_num < total_pages:
                    sleep_time = random.uniform(2, 5)
                    logger.info(f"صبر کردن به مدت {sleep_time:.2f} ثانیه قبل از استخراج صفحه بعدی...")
                    time.sleep(sleep_time)
            
            logger.info(f"استخراج تمام صفحات به پایان رسید. تعداد کل محصولات استخراج شده: {len(self.products)}")
            
        except Exception as e:
            logger.error(f"خطا در استخراج تمام صفحات: {e}")
        
        finally:
            driver.quit()
    
    def _extract_brand(self, product_name):
        """استخراج برند از نام محصول"""
        common_brands = ["Ashoka", "Al Kabeer", "Sadia", "Americana", "Khazan", "Nabil", "Birds Eye", 
                         "McCain", "Farm Fresh", "Seara", "Mezban", "Almarai", "Haagen-Dazs", "Lurpak",
                         "Al Ain", "Good Seoul", "LuLu", "Cucina", "Samho", "Quorn", "CJ", "Miratorg",
                         "Al Areesh", "Haldiram", "Bibigo", "Daim", "Toblerone", "Al Islami", "Amul",
                         "Eng Bee Tin", "Doux", "Tamoosh", "Beyond Meat", "Goodfella's", "Faani", "Al Karama",
                         "Lean Cuisine", "New York Bakery"]
        
        for brand in common_brands:
            if brand.lower() in product_name.lower():
                return brand
        
        # اگر نام محصول با کلمه شروع می‌شود، احتمالاً برند است
        parts = product_name.split()
        if len(parts) > 1 and not re.search(r'\d', parts[0]):
            return parts[0]
            
        return "N/A"
    
    def _deep_search_products(self, driver, page_url):
        """جستجوی عمیق‌تر برای یافتن محصولات بیشتر"""
        deep_products = []
        try:
            # جستجو برای همه عناصری که ممکن است محصول باشند
            product_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/'], [class*='product'], [class*='item']")
            
            for element in product_elements:
                try:
                    text = element.text.strip()
                    if not text or len(text) < 5:
                        continue
                        
                    # بررسی اینکه آیا این متن شبیه یک نام محصول است
                    if re.search(r'\b\d+\s*(?:g|kg|ml|l|pcs)\b', text, re.IGNORECASE):
                        # احتمالاً نام محصول است
                        product_name = text
                        
                        try:
                            price_element = element.find_element(By.XPATH, "./following::*[contains(@class, 'price') or contains(@data-testid, 'price')][1]")
                            price = price_element.text.strip()
                        except:
                            price = "N/A"
                            
                        weight_match = re.search(r'\b\d+\s*(?:g|kg|ml|l|pcs)\b', product_name, re.IGNORECASE)
                        weight = weight_match.group(0) if weight_match else "N/A"
                        
                        # تلاش برای یافتن URL محصول
                        try:
                            if element.tag_name == 'a':
                                product_url = element.get_attribute('href')
                            else:
                                link = element.find_element(By.XPATH, "./ancestor::a[1] | ./descendant::a[1]")
                                product_url = link.get_attribute('href')
                        except:
                            product_url = "N/A"
                            
                        # اگر این محصول قبلاً اضافه نشده، اضافه کن
                        if not any(p['product'] == product_name for p in deep_products):
                            deep_products.append({
                                'product': self._clean_product_name(product_name),
                                'brand': self._extract_brand(product_name),
                                'price': price,
                                'weight': weight,
                                'website': 'luluhypermarket.com',
                                'url': product_url,
                                'page': page_url
                            })
                            
                            logger.info(f"محصول جدید در جستجوی عمیق: {product_name} - {price}")
                        
                except Exception as e:
                    continue
        except Exception as e:
            logger.error(f"خطا در جستجوی عمیق محصولات در صفحه {page_url}: {e}")
        
        return deep_products
    
    def _clean_product_name(self, product_name):
        """حذف برند و وزن از نام محصول"""
        # حذف برند از ابتدای نام
        brand = self._extract_brand(product_name)
        if brand != "N/A":
            # حذف برند از ابتدای نام محصول
            clean_name = product_name.replace(brand, '', 1).strip()
            # حذف کاراکترهای اضافی مثل - یا : بعد از حذف برند
            clean_name = re.sub(r'^[\s\-:]+', '', clean_name)
        else:
            clean_name = product_name
            
        # حذف وزن و اندازه از انتهای نام
        weight_pattern = r'\b\d+\s*(?:g|kg|ml|l|pcs|pieces|pack|x)\b.*$'
        clean_name = re.sub(weight_pattern, '', clean_name, flags=re.IGNORECASE).strip()
        
        # حذف whitespace اضافی
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
        
        return clean_name
    
    def save_to_excel(self):
        """ذخیره داده‌ها در فایل اکسل"""
        try:
            df = pd.DataFrame(self.products)
            current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"shelfie_lulu_products_{current_datetime}.xlsx"
            writer = pd.ExcelWriter(filename, engine='xlsxwriter')
            df.to_excel(writer, index=False, sheet_name='Products')
            
            # تنظیم عرض ستون‌ها
            workbook = writer.book
            worksheet = writer.sheets['Products']
            for i, col in enumerate(df.columns):
                column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, column_width)
            
            writer.close()
            logger.info(f"داده‌ها در فایل {filename} ذخیره شدند")
            return filename
        except Exception as e:
            logger.error(f"خطا در ذخیره داده‌ها در فایل اکسل: {e}")
            return None

if __name__ == "__main__":
    # ایجاد پارسر آرگومان ها
    parser = argparse.ArgumentParser(description='استخراج محصولات از وبسایت لولو هایپرمارکت')
    parser.add_argument('--url', type=str, 
                        default="https://gcc.luluhypermarket.com/en-ae/grocery-food-cupboard-frozen-food-ready-meals-snacks",
                        help='آدرس URL دسته‌بندی محصولات برای استخراج')
    parser.add_argument('--pages', type=int, 
                        help='تعداد صفحاتی که می‌خواهید استخراج کنید (اختیاری، پیش‌فرض: همه صفحات)')
    
    # پارس کردن آرگومان‌ها
    args = parser.parse_args()
    
    # نمایش اطلاعات ورودی
    if args.pages:
        logger.info(f"شروع استخراج {args.pages} صفحه از {args.url}")
    else:
        logger.info(f"شروع استخراج تمام صفحات از {args.url}")
    
    # ایجاد اسکریپر با پارامترهای مشخص شده
    scraper = ShelfieScraper(args.url, args.pages)
    scraper.scrape_all_pages()
    
    # ذخیره داده‌ها در فایل اکسل
    output_file = scraper.save_to_excel()
    
    # نمایش پیغام پایان
    print(f"\nاستخراج با موفقیت به پایان رسید!")
    print(f"تعداد محصولات استخراج شده: {len(scraper.products)}")
    print(f"داده‌ها در فایل {output_file} ذخیره شدند.") 