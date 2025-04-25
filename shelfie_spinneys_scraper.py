import logging
import re
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
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
        logging.FileHandler("shelfie_spinneys_scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SpinneysMultiPageScraper:
    """کلاس برای استخراج داده‌های محصولات از وبسایت Spinneys"""
    
    def __init__(self, base_url, max_pages=None):
        """
        مقداردهی اولیه اسکرپر
        
        Args:
            base_url (str): URL پایه دسته‌بندی برای استخراج
            max_pages (int, optional): حداکثر تعداد صفحات برای استخراج. اگر None باشد، همه صفحات استخراج می‌شوند
        """
        self.base_url = base_url
        self.max_pages = max_pages
        self.products = []
        
    def get_total_products_and_pages(self, driver):
        """
        استخراج تعداد کل محصولات و تعداد صفحات
        
        Args:
            driver: WebDriver سلنیوم
            
        Returns:
            int: تعداد کل صفحات
        """
        try:
            # تلاش برای یافتن تعداد کل محصولات و صفحات
            logger.info("در حال استخراج تعداد کل صفحات...")
            
            # منتظر بارگزاری صفحه شود
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".pagination"))
            )
            
            # استراتژی 1: بررسی عنصر صفحه آخر در بخش pagination
            try:
                # تلاش برای یافتن آخرین دکمه صفحه
                last_page_link = driver.find_elements(By.CSS_SELECTOR, ".pagination li:not(.next) a")
                if last_page_link:
                    last_page = int(last_page_link[-1].text.strip())
                    logger.info(f"تعداد کل صفحات: {last_page}")
                    return last_page
            except Exception as e:
                logger.warning(f"خطا در استخراج آخرین صفحه از پیجینیشن: {e}")
            
            # اگر به این نقطه رسیدیم، فقط یک صفحه وجود دارد
            logger.info("فقط یک صفحه شناسایی شد")
            return 1
            
        except Exception as e:
            logger.error(f"خطا در استخراج تعداد کل صفحات: {e}")
            return 1  # فرض می‌کنیم حداقل 1 صفحه وجود دارد
    
    def scrape_page(self, driver, page_url):
        """
        استخراج اطلاعات محصولات از یک صفحه
        
        Args:
            driver: WebDriver سلنیوم
            page_url (str): آدرس صفحه برای استخراج
            
        Returns:
            list: لیستی از محصولات استخراج شده از این صفحه
        """
        page_products = []
        try:
            logger.info(f"در حال استخراج محصولات از صفحه: {page_url}")
            driver.get(page_url)
            
            # منتظر بارگزاری محصولات شود
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".product-info"))
            )
            
            # یافتن همه بلوک‌های محصول
            product_blocks = driver.find_elements(By.CSS_SELECTOR, ".product-info")
            logger.info(f"تعداد {len(product_blocks)} محصول در این صفحه یافت شد")
            
            for product_block in product_blocks:
                try:
                    # استخراج نام محصول
                    product_element = product_block.find_element(By.CSS_SELECTOR, ".product-name a")
                    product_name = product_element.text.strip()
                    product_url = product_element.get_attribute('href')
                    
                    # استخراج قیمت محصول
                    price_element = product_block.find_element(By.CSS_SELECTOR, ".product-price .price")
                    price = price_element.text.strip()
                    
                    # استخراج برند و وزن محصول از نام محصول
                    brand = self._extract_brand(product_name)
                    weight = self._extract_weight(product_name)
                    
                    # اضافه کردن به لیست محصولات
                    page_products.append({
                        'product': self._clean_product_name(product_name),
                        'brand': brand,
                        'price': price,
                        'weight': weight,
                        'website': 'spinneys.com',
                        'url': product_url,
                        'page': page_url
                    })
                    
                except Exception as e:
                    logger.warning(f"خطا در استخراج اطلاعات محصول: {e}")
                    continue
            
            logger.info(f"استخراج {len(page_products)} محصول از صفحه {page_url} با موفقیت انجام شد")
            return page_products
            
        except Exception as e:
            logger.error(f"خطا در استخراج صفحه {page_url}: {e}")
            return []
    
    def scrape_all_pages(self):
        """
        استخراج تمام صفحات محصولات
        """
        logger.info(f"شروع استخراج از URL: {self.base_url}")
        
        # راه‌اندازی ChromeDriver
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # اجرا در حالت headless
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        try:
            # رفتن به URL اصلی
            driver.get(self.base_url)
            
            # استخراج تعداد کل صفحات
            total_pages = self.get_total_products_and_pages(driver)
            
            # اگر max_pages تنظیم شده باشد، از مقدار کمتر استفاده می‌کنیم
            if self.max_pages is not None:
                total_pages = min(total_pages, self.max_pages)
                
            logger.info(f"تعداد کل صفحات برای استخراج: {total_pages}")
            
            # استخراج صفحه اول
            first_page_products = self.scrape_page(driver, self.base_url)
            self.products.extend(first_page_products)
            
            # استخراج صفحات بعدی
            for page_num in range(2, total_pages + 1):
                # ساخت URL صفحه بعدی
                page_url = f"{self.base_url}?page={page_num}"
                
                # استخراج صفحه
                page_products = self.scrape_page(driver, page_url)
                self.products.extend(page_products)
                
                # وقفه کوتاه بین استخراج صفحات
                time.sleep(2)
            
            logger.info(f"استخراج تمام شد. تعداد کل محصولات استخراج شده: {len(self.products)}")
            
        except Exception as e:
            logger.error(f"خطا در استخراج صفحات: {e}")
        finally:
            driver.quit()
    
    def _extract_brand(self, product_name):
        """
        استخراج برند از نام محصول
        
        Args:
            product_name (str): نام کامل محصول
            
        Returns:
            str: نام برند یا "N/A" اگر شناسایی نشود
        """
        # الگوی عمومی: اولین کلمه یا کلمات قبل از اولین space یا dash
        first_word_match = re.match(r'^([\w\s]+?)[\s\-]', product_name)
        if first_word_match:
            return first_word_match.group(1).strip()
        
        # اگر نتوانستیم برند را استخراج کنیم
        return "N/A"
    
    def _extract_weight(self, product_name):
        """
        استخراج وزن/اندازه محصول از نام محصول
        
        Args:
            product_name (str): نام کامل محصول
            
        Returns:
            str: وزن یا اندازه محصول یا "N/A" اگر شناسایی نشود
        """
        # الگوهای مختلف برای وزن محصول
        weight_patterns = [
            r'(\d+[\.\d]*\s*(?:g|kg|ml|l|pcs|pieces|pack|x\d+))\b',
            r'(\d+[\.\d]*\s*(?:G|KG|ML|L|PCS|PIECES|PACK|X\d+))\b',
            r'(\d+[\.\d]*\s*(?:گرم|کیلوگرم|میلی لیتر|لیتر|عدد|بسته))\b'
        ]
        
        for pattern in weight_patterns:
            match = re.search(pattern, product_name, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "N/A"
    
    def _clean_product_name(self, product_name):
        """
        پاکسازی نام محصول با حذف برند و وزن
        
        Args:
            product_name (str): نام کامل محصول
            
        Returns:
            str: نام تمیز شده محصول
        """
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
        logger.info("در حال ذخیره داده‌ها در فایل اکسل...")
        try:
            # ایجاد DataFrame از محصولات استخراج شده
            df = pd.DataFrame(self.products)
            
            current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"shelfie_spinneys_products_{current_datetime}.xlsx"
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
    parser = argparse.ArgumentParser(description='استخراج محصولات از وبسایت Spinneys')
    parser.add_argument('--url', type=str, 
                        default="https://www.spinneys.com/en-ae/catalogue/category/frozen/ready-meals",
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
    scraper = SpinneysMultiPageScraper(args.url, args.pages)
    scraper.scrape_all_pages()
    
    # ذخیره داده‌ها در فایل اکسل
    output_file = scraper.save_to_excel()
    
    # نمایش پیغام پایان
    print(f"\nاستخراج با موفقیت به پایان رسید!")
    print(f"تعداد محصولات استخراج شده: {len(scraper.products)}")
    print(f"داده‌ها در فایل {output_file} ذخیره شدند.") 