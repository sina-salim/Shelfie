"""
Shelfie - استخراج‌کننده اطلاعات محصولات از وب‌سایت Al Meera
این اسکریپت برای استخراج اطلاعات محصولات از وب‌سایت المیرا طراحی شده است.
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
        logging.FileHandler("shelfie_almeera_scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AlmeeraMultiPageScraper:
    """
    کلاس اصلی برای استخراج اطلاعات محصولات از وب‌سایت Al Meera
    """
    def __init__(self, base_url, max_pages=None):
        self.base_url = base_url.rstrip("/?pageId=")  # حذف pageId از انتهای URL در صورت وجود
        self.products = []
        self.total_pages = 1
        self.max_pages = max_pages  # تعداد صفحات تعیین شده توسط کاربر
        
    def get_total_products_and_pages(self, driver):
        """استخراج تعداد کل محصولات و محاسبه تعداد صفحات"""
        try:
            # استخراج آخرین شماره صفحه بر اساس الگوی داده شده در almeera.txt
            try:
                # روش جدید: بررسی همه لینک‌های صفحه‌بندی
                page_links = driver.find_elements(By.CSS_SELECTOR, "li.item a[title], a.item[title], a[title*='Page'], a[title^='Go to page']")
                highest_page = 1
                
                for link in page_links:
                    title = link.get_attribute("title")
                    if title and any(char.isdigit() for char in title):
                        # استخراج عدد از عنوان
                        digits = ''.join(filter(str.isdigit, title))
                        if digits:
                            page_num = int(digits)
                            if page_num > highest_page:
                                highest_page = page_num
                    
                    # همچنین بررسی pageId در href
                    href = link.get_attribute("href")
                    if href:
                        page_id_match = re.search(r'pageId=(\d+)', href)
                        if page_id_match:
                            page_id = int(page_id_match.group(1))
                            if page_id > highest_page:
                                highest_page = page_id
                
                # بررسی صریح برای المان آخرین صفحه
                last_page_elements = driver.find_elements(By.CSS_SELECTOR, "li.last-page, li.item.last-page")
                for element in last_page_elements:
                    # بررسی متن المان
                    element_text = element.text.strip()
                    if element_text and element_text.isdigit():
                        last_page = int(element_text)
                        if last_page > highest_page:
                            highest_page = last_page
                            logger.info(f"تعداد کل صفحات (از متن المان last-page): {highest_page}")
                    
                    # بررسی لینک داخل المان
                    try:
                        link_element = element.find_element(By.TAG_NAME, "a")
                        if link_element:
                            # استخراج از متن لینک
                            page_text = link_element.text.strip()
                            if page_text and page_text.isdigit():
                                last_page = int(page_text)
                                if last_page > highest_page:
                                    highest_page = last_page
                                    logger.info(f"تعداد کل صفحات (از متن لینک در المان last-page): {highest_page}")
                            
                            # استخراج از عنوان لینک
                            title = link_element.get_attribute("title")
                            if title and any(char.isdigit() for char in title):
                                digits = ''.join(filter(str.isdigit, title))
                                if digits:
                                    page_num = int(digits)
                                    if page_num > highest_page:
                                        highest_page = page_num
                                        logger.info(f"تعداد کل صفحات (از عنوان لینک در المان last-page): {highest_page}")
                            
                            # استخراج از href
                            href = link_element.get_attribute("href")
                            if href:
                                page_id_match = re.search(r'pageId=(\d+)', href)
                                if page_id_match:
                                    page_id = int(page_id_match.group(1))
                                    if page_id > highest_page:
                                        highest_page = page_id
                                        logger.info(f"تعداد کل صفحات (از href لینک در المان last-page): {highest_page}")
                    except Exception as inner_e:
                        logger.warning(f"خطا در بررسی لینک داخل المان last-page: {inner_e}")
                
                if highest_page > 1:
                    self.total_pages = highest_page
                    logger.info(f"تعداد کل صفحات تشخیص داده شده: {self.total_pages}")
                
            except Exception as e:
                logger.warning(f"خطا در استخراج شماره آخرین صفحه: {e}")
                
                # روش جایگزین: بررسی همه لینک‌های صفحه‌بندی با سلکتور ساده‌تر
                try:
                    page_links = driver.find_elements(By.CSS_SELECTOR, "li.item a, a.item, .pager a")
                    highest_page = 1
                    
                    for link in page_links:
                        # بررسی متن لینک
                        text = link.text.strip()
                        if text and text.isdigit():
                            page_num = int(text)
                            if page_num > highest_page:
                                highest_page = page_num
                                logger.info(f"صفحه شماره {page_num} پیدا شد (از متن لینک)")
                        
                        # بررسی عنوان لینک
                        title = link.get_attribute("title")
                        if title and any(char.isdigit() for char in title):
                            digits = ''.join(filter(str.isdigit, title))
                            if digits:
                                page_num = int(digits)
                                if page_num > highest_page:
                                    highest_page = page_num
                                    logger.info(f"صفحه شماره {page_num} پیدا شد (از عنوان لینک)")
                        
                        # بررسی href
                        href = link.get_attribute("href")
                        if href:
                            page_id_match = re.search(r'pageId=(\d+)', href)
                            if page_id_match:
                                page_id = int(page_id_match.group(1))
                                if page_id > highest_page:
                                    highest_page = page_id
                                    logger.info(f"صفحه شماره {page_id} پیدا شد (از href لینک)")
                    
                    if highest_page > 1:
                        self.total_pages = highest_page
                        logger.info(f"تعداد کل صفحات (از همه لینک‌ها): {self.total_pages}")
                except Exception as e:
                    logger.warning(f"خطا در روش جایگزین استخراج تعداد صفحات: {e}")
            
            # بررسی صریح برای وجود دکمه صفحه بعد
            next_page_buttons = driver.find_elements(By.CSS_SELECTOR, "li.next-page a, a.next, a[rel='next'], a[title*='next'], a[class*='next']")
            
            # اگر هنوز تعداد صفحات پیدا نشده، اما دکمه صفحه بعد موجود است
            if self.total_pages == 1 and next_page_buttons:
                logger.info("دکمه صفحه بعد یافت شد، اما تعداد کل صفحات مشخص نیست.")
                
                # تلاش برای پیمایش تا آخرین صفحه با کلیک روی دکمه صفحه بعد
                try:
                    logger.info("تلاش برای پیمایش به آخرین صفحه...")
                    current_page = 1
                    max_attempts = 30  # محدودیت تعداد صفحات برای جلوگیری از حلقه نامحدود
                    
                    # ذخیره URL صفحه فعلی برای برگشت به آن
                    original_url = driver.current_url
                    
                    while current_page < max_attempts:
                        # یافتن دکمه صفحه بعد
                        next_buttons = driver.find_elements(By.CSS_SELECTOR, "li.next-page a, a.next, a[rel='next'], a[title*='next'], a[class*='next']")
                        if not next_buttons:
                            # رسیدن به آخرین صفحه
                            logger.info(f"آخرین صفحه یافت شد: {current_page}")
                            self.total_pages = current_page
                            break
                        
                        # کلیک روی دکمه صفحه بعد
                        current_url = driver.current_url
                        try:
                            next_buttons[0].click()
                            # انتظار برای تغییر URL
                            WebDriverWait(driver, 5).until(lambda d: d.current_url != current_url)
                            current_page += 1
                            logger.info(f"رفتن به صفحه {current_page}...")
                        except Exception as click_error:
                            logger.warning(f"خطا در کلیک روی دکمه صفحه بعد: {click_error}")
                            break
                    
                    # برگشت به صفحه اول
                    logger.info(f"برگشت به صفحه اول: {original_url}")
                    driver.get(original_url)
                    
                    # انتظار برای بارگذاری صفحه
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                except Exception as e:
                    logger.error(f"خطا در پیمایش صفحات: {e}")
                    # در صورت خطا، تعداد صفحات پیش‌فرض را تنظیم می‌کنیم
                    self.total_pages = 10  # مقدار پیش‌فرض بالاتر
            
            # اگر هنوز تعداد صفحات پیدا نشده، مقدار پیش‌فرض را استفاده می‌کنیم
            if self.total_pages == 1 and next_page_buttons:
                # اگر دکمه next-page وجود دارد، حداقل 10 صفحه را در نظر می‌گیریم
                self.total_pages = 10  # افزایش مقدار پیش‌فرض
                logger.info(f"دکمه next-page یافت شد. تعداد صفحات پیش‌فرض: {self.total_pages}")
            
            # اگر کاربر تعداد صفحات را مشخص کرده، آن را اعمال می‌کنیم
            if self.max_pages is not None:
                logger.info(f"محدود کردن تعداد صفحات به حداکثر {self.max_pages} (تعیین شده توسط کاربر)")
                self.total_pages = min(self.total_pages, self.max_pages)
                logger.info(f"تعداد نهایی صفحات برای استخراج: {self.total_pages}")
                
            return self.total_pages
                
        except Exception as e:
            logger.error(f"خطا در استخراج تعداد کل صفحات: {e}")
            # در صورت خطا، مقدار پیش‌فرض بالاتر را استفاده می‌کنیم
            default_pages = 10
            if self.max_pages is not None:
                default_pages = min(default_pages, self.max_pages)
            logger.info(f"استفاده از تعداد صفحات پیش‌فرض: {default_pages}")
            return default_pages
    
    def scrape_page(self, driver, page_url):
        """استخراج محصولات از یک صفحه خاص"""
        try:
            logger.info(f"استخراج محصولات از صفحه: {page_url}")
            
            # بارگذاری صفحه
            driver.get(page_url)
            
            # انتظار برای بارگذاری محصولات
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.product-cell, div.product"))
                )
            except TimeoutException:
                logger.warning(f"بارگذاری محصولات در صفحه {page_url} با تایم‌اوت مواجه شد")
            
            # اسکرول به پایین برای بارگذاری همه محصولات
            total_height = driver.execute_script("return document.body.scrollHeight")
            for i in range(1, 10):  # اسکرول تا 10 بار برای بارگذاری محتوای بیشتر
                driver.execute_script(f"window.scrollTo(0, {i * total_height / 10});")
                time.sleep(0.5)
            
            # استخراج HTML صفحه
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # یافتن همه محصولات با سلکتورهای مختلف، به جز آنهایی که در سایدبار هستند
            product_elements = []
            
            # ابتدا همه محصولات را پیدا می‌کنیم
            all_product_elements = soup.select("li.product-cell.box-product, div.product")
            
            if not all_product_elements:
                # سلکتور جایگزین اگر محصولی یافت نشد
                all_product_elements = soup.select("div.product-cell, div[class*='product-item']")
            
            # جدا کردن محصولات اصلی از محصولات سایدبار
            for elem in all_product_elements:
                # بررسی اینکه آیا این محصول در سایدبار قرار دارد یا خیر
                is_in_sidebar = False
                parent = elem
                # بررسی همه والدین تا رسیدن به بدنه سند
                for _ in range(10):  # حداکثر 10 سطح بالاتر را بررسی می‌کنیم
                    if parent is None:
                        break
                    if parent.get('id') == 'sidebar-first' or 'sidebar' in parent.get('class', []):
                        is_in_sidebar = True
                        break
                    parent = parent.parent
                
                if not is_in_sidebar:
                    product_elements.append(elem)
            
            logger.info(f"تعداد محصولات یافت شده در صفحه (به جز سایدبار): {len(product_elements)}")
            
            page_products = []
            # لیست برای ذخیره نام محصولات برای جلوگیری از تکرار
            product_names_seen = set()
            
            # استخراج محصولات
            for product_elem in product_elements:
                try:
                    # استخراج نام محصول
                    product_name_elem = product_elem.select_one("h5.product-name a, a.product-name, a.fn, a[class*='name']")
                    if not product_name_elem:
                        continue
                        
                    product_name = product_name_elem.text.strip()
                    
                    # اگر این محصول قبلاً دیده شده است، آن را نادیده می‌گیریم
                    if product_name in product_names_seen:
                        logger.info(f"محصول تکراری نادیده گرفته شد: {product_name}")
                        continue
                    
                    # افزودن نام محصول به لیست محصولات دیده شده
                    product_names_seen.add(product_name)
                    
                    product_url = product_name_elem.get('href', '')
                    if product_url and not product_url.startswith('http'):
                        product_url = 'https://almeera.online/' + product_url
                    
                    # استخراج قیمت
                    price_elem = product_elem.select_one("span.price.product-price, div.product-price span, [class*='price']")
                    price = price_elem.text.strip() if price_elem else "N/A"
                    
                    # استخراج وزن از نام محصول
                    weight_match = re.search(r'\b\d+\s*(?:g|kg|ml|l|pcs)\b', product_name, re.IGNORECASE)
                    weight = weight_match.group(0) if weight_match else "N/A"
                    
                    # استخراج تصویر محصول
                    img_elem = product_elem.select_one("img.photo, img[class*='product']")
                    img_url = ""
                    if img_elem:
                        img_url = img_elem.get('src', '')
                        if img_url and not img_url.startswith('http'):
                            if img_url.startswith('//'):
                                img_url = 'https:' + img_url
                            else:
                                img_url = 'https://almeera.online/' + img_url
                    
                    # تمیز کردن قیمت
                    price = re.sub(r'[^\d\.,]', '', price).strip()
                    
                    # اضافه کردن به لیست محصولات صفحه
                    page_products.append({
                        'product': self._clean_product_name(product_name),
                        'brand': self._extract_brand(product_name),
                        'price': price,
                        'weight': weight,
                        'url': product_url,
                        'page': page_url
                    })
                    
                    logger.info(f"محصول استخراج شد: {product_name} - {price}")
                except Exception as e:
                    logger.error(f"خطا در استخراج محصول: {e}")
            
            # اگر هیچ محصولی پیدا نشد، سعی کنید با روش JavaScript محصولات را پیدا کنید
            if len(page_products) == 0:
                logger.info("تلاش برای استخراج محصولات با JavaScript...")
                try:
                    # استخراج همه المنت‌های محصول با کوئری‌سلکتور، به جز آنهایی که در سایدبار هستند
                    product_elements_js = driver.execute_script("""
                        return Array.from(document.querySelectorAll('.product, .product-cell, [class*="product-item"]'))
                        .filter(el => {
                            // بررسی اینکه آیا المان در سایدبار قرار دارد یا خیر
                            let parent = el;
                            while (parent) {
                                if (parent.id === 'sidebar-first' || 
                                    (parent.className && parent.className.includes('sidebar'))) {
                                    return false;
                                }
                                parent = parent.parentElement;
                            }
                            return true;
                        })
                        .map(el => {
                            let nameEl = el.querySelector('h5 a, a.product-name, a.fn, a[class*="name"], .product-name a');
                            let priceEl = el.querySelector('span.price, [class*="price"]');
                            let imgEl = el.querySelector('img');
                            
                            return {
                                name: nameEl ? nameEl.textContent.trim() : '',
                                url: nameEl ? nameEl.href : '',
                                price: priceEl ? priceEl.textContent.trim() : '',
                                image: imgEl ? imgEl.src : ''
                            };
                        }).filter(item => item.name && item.name.length > 0);
                    """)
                    
                    for product_data in product_elements_js:
                        if product_data.get('name'):
                            product_name = product_data.get('name')
                            
                            # اگر این محصول قبلاً دیده شده است، آن را نادیده می‌گیریم
                            if product_name in product_names_seen:
                                logger.info(f"محصول تکراری نادیده گرفته شد (JavaScript): {product_name}")
                                continue
                            
                            # افزودن نام محصول به لیست محصولات دیده شده
                            product_names_seen.add(product_name)
                            
                            product_url = product_data.get('url', '')
                            price = product_data.get('price', 'N/A')
                            
                            # استخراج وزن از نام محصول
                            weight_match = re.search(r'\b\d+\s*(?:g|kg|ml|l|pcs)\b', product_name, re.IGNORECASE)
                            weight = weight_match.group(0) if weight_match else "N/A"
                            
                            # تمیز کردن قیمت
                            price = re.sub(r'[^\d\.,]', '', price).strip()
                            
                            # اضافه کردن به لیست محصولات صفحه
                            page_products.append({
                                'product': self._clean_product_name(product_name),
                                'brand': self._extract_brand(product_name),
                                'price': price,
                                'weight': weight,
                                'url': product_url,
                                'page': page_url
                            })
                            
                            logger.info(f"محصول استخراج شد با JavaScript: {product_name} - {price}")
                except Exception as e:
                    logger.error(f"خطا در استخراج محصولات با JavaScript: {e}")
            
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
            first_page_url = f"{self.base_url}"
            logger.info(f"بارگذاری صفحه اول: {first_page_url}")
            driver.get(first_page_url)
            
            # انتظار برای بارگذاری صفحه
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # استخراج تعداد کل صفحات
            total_pages = self.get_total_products_and_pages(driver)
            logger.info(f"تعداد کل صفحات برای استخراج: {total_pages}")
            
            # استخراج محصولات از هر صفحه
            for page_num in range(1, total_pages + 1):
                if page_num == 1:
                    page_url = f"{self.base_url}"
                else:
                    page_url = f"{self.base_url}/?pageId={page_num}"
                
                # اطمینان از اینکه URL صحیح است
                if "frozen-foo" in page_url and "frozen-food" not in page_url:
                    page_url = page_url.replace("frozen-foo", "frozen-food")
                
                logger.info(f"استخراج صفحه {page_num} از {total_pages}: {page_url}")
                page_products = self.scrape_page(driver, page_url)
                
                # بررسی نتیجه استخراج
                if not page_products:
                    logger.warning(f"هیچ محصولی در صفحه {page_num} یافت نشد: {page_url}")
                    # آیا باید یک تلاش مجدد انجام دهیم؟
                    logger.info("تلاش مجدد برای استخراج صفحه...")
                    time.sleep(3)  # تاخیر کوتاه قبل از تلاش مجدد
                    page_products = self.scrape_page(driver, page_url)
                    
                    if not page_products:
                        logger.warning(f"تلاش مجدد هم ناموفق بود. ادامه به صفحه بعد...")
                
                # افزودن محصولات این صفحه به لیست کلی
                self.products.extend(page_products)
                logger.info(f"تعداد محصولات استخراج شده تا کنون: {len(self.products)}")
                
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
        common_brands = ["WATTIES", "Al Alali", "American Garden", "Ardo", "Betty Crocker", "Birds Eye", 
                         "Findus", "Frigo", "Haagen-Dazs", "Iceland", "Kellogg's", "Lurpak", "McCain",
                         "Pillsbury", "Sara Lee", "Sadia", "Farm Fresh", "Iglo", "Green Isle", "Americana", 
                         "Green Giant", "Kiri", "La Vache Qui Rit", "Philadelphia", "Galbani", "Doux", 
                         "Almarai", "Quorn", "Beyond Meat", "Baskin Robbins", "London Dairy"]
        
        for brand in common_brands:
            if brand.upper() in product_name.upper():
                return brand
        
        # اگر نام محصول با کلمه حروف بزرگ شروع می‌شود، احتمالاً برند است
        parts = product_name.split()
        if len(parts) > 1 and parts[0].isupper() and not re.search(r'\d', parts[0]):
            return parts[0]
            
        return "N/A"
    
    def _clean_product_name(self, product_name):
        """حذف برند و وزن از نام محصول"""
        # حذف برند از ابتدای نام
        brand = self._extract_brand(product_name)
        if brand != "N/A":
            # حذف برند از ابتدای نام محصول با اطمینان بیشتر
            if product_name.upper().startswith(brand.upper()):
                clean_name = product_name[len(brand):].strip()
            else:
                # جستجوی دقیق برند و حذف آن
                clean_name = re.sub(rf'\b{re.escape(brand)}\b', '', product_name, flags=re.IGNORECASE).strip()
            
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
            # تبدیل لیست محصولات به دیتافریم
            df = pd.DataFrame(self.products)
            
            # حذف ستون‌های image_url و website اگر وجود داشته باشند
            columns_to_drop = []
            if 'image_url' in df.columns:
                columns_to_drop.append('image_url')
            if 'website' in df.columns:
                columns_to_drop.append('website')
            
            if columns_to_drop:
                df = df.drop(columns=columns_to_drop)
                logger.info(f"ستون‌های حذف شده از خروجی: {', '.join(columns_to_drop)}")
            
            # حذف ردیف‌های تکراری بر اساس نام محصول
            df = df.drop_duplicates(subset=['product'])
            logger.info(f"تعداد محصولات پس از حذف موارد تکراری: {len(df)}")
            
            current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"shelfie_almeera_products_{current_datetime}.xlsx"
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
    parser = argparse.ArgumentParser(description='استخراج محصولات از وبسایت Al Meera')
    parser.add_argument('--url', type=str, 
                        default="https://almeera.online/frozen-food",
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
    scraper = AlmeeraMultiPageScraper(args.url, args.pages)
    scraper.scrape_all_pages()
    
    # ذخیره داده‌ها در فایل اکسل
    output_file = scraper.save_to_excel()
    
    # نمایش پیغام پایان
    print(f"\nاستخراج با موفقیت به پایان رسید!")
    print(f"تعداد محصولات استخراج شده: {len(scraper.products)}")
    print(f"داده‌ها در فایل {output_file} ذخیره شدند.") 