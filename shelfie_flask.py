from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import pandas as pd
import logging
import os
import threading
import traceback
from datetime import datetime
from unioncoop_scraper import UnionCoopMultiPageScraper
from shelfie_lulu_scraper import ShelfieScraper as LuluMultiPageScraper
from shelfie_spinneys_scraper import SpinneysMultiPageScraper
from almeera_scraper import AlmeeraMultiPageScraper

# تنظیم لاگر
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("shelfie_flask.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# وضعیت کلی برنامه
class ScraperState:
    def __init__(self):
        self.scraper_running = False
        self.progress = 0
        self.total_pages = 0
        self.current_page = 0
        self.products = []
        self.log_messages = []
        self.output_file = None
        self.notification_message = ""
        self.show_notification = False

state = ScraperState()

# مسیر ذخیره فایل‌ها
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_scraping', methods=['POST'])
def start_scraping():
    if state.scraper_running:
        return jsonify({'status': 'error', 'message': 'یک فرآیند استخراج در حال اجراست'})
    
    try:
        store_type = request.form.get('store_type')
        url = request.form.get('url')
        use_max_pages = request.form.get('use_max_pages') == 'true'
        max_pages = int(request.form.get('max_pages', 1)) if use_max_pages else None
        use_multi_category = request.form.get('use_multi_category') == 'true'
        
        # اگر چندین دسته‌بندی انتخاب شده است
        categories = None
        if use_multi_category:
            categories = request.form.getlist('categories[]')
        
        # راه‌اندازی Thread جدید برای استخراج
        thread = threading.Thread(
            target=run_scraper, 
            args=(url, max_pages, categories, store_type)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'success', 'message': 'استخراج آغاز شد'})
    
    except Exception as e:
        logger.error(f"خطا در شروع استخراج: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'خطا: {str(e)}'})

@app.route('/status')
def get_status():
    """ارائه وضعیت فعلی اسکرپر به صورت JSON"""
    return jsonify({
        'scraper_running': state.scraper_running,
        'progress': state.progress,
        'total_pages': state.total_pages,
        'current_page': state.current_page,
        'product_count': len(state.products),
        'logs': state.log_messages[-50:] if state.log_messages else [],
        'output_file': state.output_file,
        'notification_message': state.notification_message,
        'show_notification': state.show_notification
    })

@app.route('/download/<filename>')
def download_file(filename):
    """دانلود فایل اکسل"""
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        logger.error(f"خطا در دانلود فایل: {e}")
        return jsonify({'status': 'error', 'message': f'خطا در دانلود فایل: {str(e)}'})

@app.route('/download_csv')
def download_csv():
    """تبدیل به CSV و دانلود"""
    try:
        if not state.products:
            return jsonify({'status': 'error', 'message': 'هیچ محصولی برای دانلود وجود ندارد'})
        
        df = pd.DataFrame(state.products)
        csv_filename = f"shelfie_products_export_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        return send_file(csv_path, as_attachment=True)
    except Exception as e:
        logger.error(f"خطا در تبدیل به CSV: {e}")
        return jsonify({'status': 'error', 'message': f'خطا در تبدیل به CSV: {str(e)}'})

@app.route('/clear_logs', methods=['POST'])
def clear_logs():
    """پاک کردن لاگ‌ها"""
    state.log_messages = []
    return jsonify({'status': 'success'})

def run_scraper(url, max_pages=None, categories=None, store_type="Lulu Hypermarket"):
    """اجرای اسکرپر در thread جداگانه"""
    try:
        # تنظیم وضعیت اولیه
        state.scraper_running = True
        state.progress = 0
        state.products = []
        state.current_page = 0
        state.log_messages = []
        state.output_file = None
        state.show_notification = False
        
        # اضافه کردن لاگ‌های شروع
        logger.info("شروع فرآیند استخراج محصولات...")
        state.log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - شروع فرآیند استخراج محصولات...")
        
        logger.info(f"فروشگاه: {store_type}")
        state.log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - فروشگاه: {store_type}")
        
        logger.info(f"URL استخراج: {url}")
        state.log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - URL استخراج: {url}")
        
        if max_pages:
            logger.info(f"تعداد صفحات برای استخراج: {max_pages}")
            state.log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - تعداد صفحات برای استخراج: {max_pages}")
        else:
            logger.info("استخراج تمام صفحات موجود")
            state.log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - استخراج تمام صفحات موجود")
        
        # اگر چندین دسته‌بندی انتخاب شده باشد
        if categories and len(categories) > 0:
            all_products = []
            state.total_pages = 0
            
            for i, category in enumerate(categories):
                logger.info(f"شروع استخراج دسته‌بندی {i+1} از {len(categories)}: {category}")
                state.log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - شروع استخراج دسته‌بندی {i+1} از {len(categories)}: {category}")
                
                if store_type == "Lulu Hypermarket":
                    category_url = f"{url}/{category}"
                    scraper = LuluMultiPageScraper(category_url, max_pages)
                elif store_type == "Spinneys":
                    category_base_url = "https://www.spinneys.com/en-ae/catalogue/category"
                    category_url = f"{category_base_url}/{category}"
                    scraper = SpinneysMultiPageScraper(category_url, max_pages)
                elif store_type == "Union Coop":
                    category_base_url = "https://www.unioncoop.ae/frozen-food-sea-food-butter-ice-cream.html"
                    category_url = f"{category_base_url}/{category}"
                    scraper = UnionCoopMultiPageScraper(category_url, max_pages)
                else:  # Almeera
                    category_base_url = "https://almeera.online"
                    category_url = f"{category_base_url}/{category}"
                    scraper = AlmeeraMultiPageScraper(category_url, max_pages)
                
                # Monkey patching برای نمایش پیشرفت
                original_scrape_page = scraper.scrape_page
                def scrape_page_with_progress(driver, page_url):
                    state.current_page += 1
                    state.progress = min(95, int((state.current_page / state.total_pages) * 100))
                    log_msg = f"استخراج صفحه {state.current_page} از {state.total_pages}"
                    state.log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
                    return original_scrape_page(driver, page_url)
                scraper.scrape_page = scrape_page_with_progress
                
                # Monkey patching برای دریافت تعداد صفحات
                original_get_total_pages = scraper.get_total_products_and_pages
                def get_total_pages_with_update(driver):
                    total_pages = original_get_total_pages(driver)
                    state.total_pages += total_pages
                    log_msg = f"تعداد کل صفحات: {state.total_pages}"
                    state.log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
                    return total_pages
                scraper.get_total_products_and_pages = get_total_pages_with_update
                
                scraper.scrape_all_pages()
                all_products.extend(scraper.products)
                
                if i < len(categories) - 1:
                    import time
                    time.sleep(5)
            
            # ذخیره همه محصولات در یک فایل
            if all_products:
                df = pd.DataFrame(all_products)
                try:
                    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    store_prefix = "lulu" if store_type == "Lulu Hypermarket" else ("spinneys" if store_type == "Spinneys" else ("unioncoop" if store_type == "Union Coop" else "almeera"))
                    filename = f"shelfie_{store_prefix}_multi_category_{current_datetime}.xlsx"
                    
                    # ذخیره به اکسل
                    writer = pd.ExcelWriter(filename, engine='xlsxwriter')
                    df.to_excel(writer, index=False, sheet_name='Products')
                    
                    # تنظیم عرض ستون‌ها
                    workbook = writer.book
                    worksheet = writer.sheets['Products']
                    for i, col in enumerate(df.columns):
                        column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                        worksheet.set_column(i, i, column_width)
                    
                    writer.close()
                    
                    state.output_file = filename
                    log_msg = f"تمام محصولات در فایل {filename} ذخیره شدند"
                    logger.info(log_msg)
                    state.log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
                    
                    # نمایش اعلان موفقیت
                    state.notification_message = f"فایل اکسل با موفقیت ذخیره شد: {filename}"
                    state.show_notification = True
                    
                except Exception as e:
                    error_msg = f"خطا در ذخیره فایل: {e}"
                    logger.error(error_msg)
                    state.log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - خطا: {error_msg}")
            
            state.products = all_products
            state.progress = 100
            
        else:
            # استخراج از یک URL
            if store_type == "Lulu Hypermarket":
                scraper = LuluMultiPageScraper(url, max_pages)
            elif store_type == "Spinneys":
                scraper = SpinneysMultiPageScraper(url, max_pages)
            elif store_type == "Union Coop":
                scraper = UnionCoopMultiPageScraper(url, max_pages)
            else:  # Almeera
                scraper = AlmeeraMultiPageScraper(url, max_pages)
            
            # Monkey patching برای نمایش پیشرفت
            original_scrape_page = scraper.scrape_page
            def scrape_page_with_progress(driver, page_url):
                state.current_page += 1
                state.progress = min(95, int((state.current_page / state.total_pages) * 100))
                log_msg = f"استخراج صفحه {state.current_page} از {state.total_pages}"
                state.log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
                return original_scrape_page(driver, page_url)
            scraper.scrape_page = scrape_page_with_progress
            
            # Monkey patching برای دریافت تعداد صفحات
            original_get_total_pages = scraper.get_total_products_and_pages
            def get_total_pages_with_update(driver):
                total_pages = original_get_total_pages(driver)
                state.total_pages = total_pages
                log_msg = f"تعداد کل صفحات: {state.total_pages}"
                state.log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
                return total_pages
            scraper.get_total_products_and_pages = get_total_pages_with_update
            
            scraper.scrape_all_pages()
            state.products = scraper.products
            
            # ذخیره نتایج در اکسل
            output_file = scraper.save_to_excel()
            state.output_file = output_file
            
            # نمایش اعلان موفقیت
            if output_file:
                state.notification_message = f"فایل اکسل با موفقیت ذخیره شد: {output_file}"
                state.show_notification = True
            
            state.progress = 100
        
        log_msg = f"استخراج با موفقیت به پایان رسید. تعداد محصولات استخراج شده: {len(state.products)}"
        logger.info(log_msg)
        state.log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - {log_msg}")
        
    except Exception as e:
        error_msg = f"خطا در استخراج محصولات: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        state.log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - خطا: {error_msg}")
    finally:
        state.scraper_running = False

if __name__ == '__main__':
    app.run(debug=True) 