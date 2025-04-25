// تغییر رنگ پس‌زمینه هنگام اسکرول
document.addEventListener('DOMContentLoaded', function() {
    // تعریف رنگ‌های اولیه و نهایی
    const startColor = { r: 232, g: 34, b: 39 }; // قرمز (#e82227)
    const endColor = { r: 255, g: 165, b: 0 };   // نارنجی (#ffa500)
    
    // محاسبه ارتفاع قابل اسکرول صفحه
    function getMaxScroll() {
        return document.documentElement.scrollHeight - window.innerHeight;
    }
    
    // تبدیل اعداد RGB به فرمت رشته‌ای CSS
    function rgbToString(rgb) {
        return `rgb(${Math.round(rgb.r)}, ${Math.round(rgb.g)}, ${Math.round(rgb.b)})`;
    }
    
    // محاسبه رنگ بر اساس میزان اسکرول
    function calculateColor(scrollPosition, maxScroll) {
        // محاسبه درصد اسکرول
        const scrollPercentage = Math.min(scrollPosition / maxScroll, 1);
        
        // محاسبه رنگ جدید با درون‌یابی خطی بین رنگ شروع و پایان
        return {
            r: startColor.r + (endColor.r - startColor.r) * scrollPercentage,
            g: startColor.g + (endColor.g - startColor.g) * scrollPercentage,
            b: startColor.b + (endColor.b - startColor.b) * scrollPercentage
        };
    }
    
    // بروزرسانی رنگ پس‌زمینه
    function updateBackgroundColor() {
        const scrollPosition = window.scrollY;
        const maxScroll = getMaxScroll();
        const newColor = calculateColor(scrollPosition, maxScroll);
        
        // اعمال گرادیان ثابت به کل صفحه با تغییر رنگ پایین گرادیان بر اساس اسکرول
        document.body.style.background = `linear-gradient(180deg, #000000 40%, ${rgbToString(newColor)} 110%)`;
        document.body.style.backgroundAttachment = 'fixed';
        document.body.style.backgroundSize = 'cover';
        document.body.style.minHeight = '100vh';
    }
    
    // اضافه کردن رویداد اسکرول
    window.addEventListener('scroll', updateBackgroundColor);
    
    // اضافه کردن رویداد تغییر اندازه پنجره
    window.addEventListener('resize', updateBackgroundColor);
    
    // اجرای اولیه برای تنظیم رنگ اولیه
    updateBackgroundColor();
});




// تنظیمات دسته‌بندی‌ها برای هر فروشگاه
const storeCategories = {
    'Lulu Hypermarket': [
        { value: 'grocery-food-cupboard-fresh-food', text: 'Fresh Food' },
        { value: 'grocery-food-cupboard-dairy-eggs', text: 'Dairy & Eggs' },
        { value: 'grocery-food-cupboard-frozen-food-ready-meals-snacks', text: 'Frozen Food & Ready Meals' },
        { value: 'grocery-food-cupboard-beverages', text: 'Beverages' },
        { value: 'grocery-food-cupboard-world-foods', text: 'World Foods' },
        { value: 'grocery-food-cupboard-breakfast-bakery', text: 'Breakfast & Bakery' },
        { value: 'grocery-food-cupboard-canned-food', text: 'Canned Food' }
    ],
    'Spinneys': [
        { value: 'frozen/ready-meals', text: 'Ready Meals' },
        { value: 'frozen/chips-potatoes', text: 'Chips & Potatoes' },
        { value: 'frozen/meat-poultry', text: 'Meat & Poultry' },
        { value: 'frozen/vegetables', text: 'Vegetables' },
        { value: 'frozen/fruits-smoothies', text: 'Fruits & Smoothies' },
        { value: 'frozen/bakery', text: 'Bakery' },
        { value: 'frozen/ice-cream-desserts', text: 'Ice Cream & Desserts' }
    ],
    'Union Coop': [
        { value: 'frozen-food', text: 'Frozen Food' },
        { value: 'frozen-desserts', text: 'Frozen Desserts' },
        { value: 'frozen-snacks', text: 'Frozen Snacks' },
        { value: 'frozen-beverages', text: 'Frozen Beverages' },
        { value: 'frozen-vegetables', text: 'Frozen Vegetables' },
        { value: 'frozen-fruits', text: 'Frozen Fruits' },
        { value: 'frozen-meats', text: 'Frozen Meats' }
    ],
    'Almeera': [
        { value: 'frozen-food', text: 'Frozen Food' },
        { value: 'frozen-desserts', text: 'Frozen Desserts' },
        { value: 'frozen-snacks', text: 'Frozen Snacks' },
        { value: 'frozen-beverages', text: 'Frozen Beverages' },
        { value: 'frozen-vegetables', text: 'Frozen Vegetables' },
        { value: 'frozen-fruits', text: 'Frozen Fruits' },
        { value: 'frozen-meats', text: 'Frozen Meats' }
    ]
};

// تنظیمات URL پیش‌فرض برای هر فروشگاه
const defaultURLs = {
    'Lulu Hypermarket': 'https://gcc.luluhypermarket.com/en-ae/grocery-food-cupboard-frozen-food-ready-meals-snacks',
    'Spinneys': 'https://www.spinneys.com/en-ae/catalogue/category/frozen/ready-meals',
    'Union Coop': 'https://www.unioncoop.ae/frozen-food-sea-food-butter-ice-cream.html',
    'Almeera': 'https://almeera.online/frozen-food/'
};

// متغیرهای سراسری
let isRunning = false;
let statusInterval = null;
let toast = null;

// رویدادهای DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    // مقداردهی تست
    toast = new bootstrap.Toast(document.querySelector('.toast'));
    
    // اضافه کردن شنونده رویداد برای فرم استخراج
    setupFormListeners();
    
    // اضافه کردن شنونده رویداد برای دکمه پاک کردن لاگ‌ها
    document.getElementById('clear-logs').addEventListener('click', clearLogs);
    
    // به‌روزرسانی اولیه گزینه‌های دسته‌بندی
    updateCategoriesDropdown('Lulu Hypermarket');
});

// تنظیم شنونده‌های رویداد فرم
function setupFormListeners() {
    // تغییر فروشگاه
    document.querySelectorAll('input[name="store_type"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const storeType = this.value;
            updateCategoriesDropdown(storeType);
        });
    });
    
    // تغییر نوع URL
    document.querySelectorAll('input[name="url_type"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const urlType = this.value;
            const urlInput = document.querySelector('.custom-url-input');
            
            if (urlType === 'custom') {
                urlInput.style.display = 'block';
            } else {
                urlInput.style.display = 'none';
            }
        });
    });
    
    // تغییر گزینه تعداد صفحات
    document.querySelectorAll('input[name="pages_option"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const pagesOption = this.value;
            const specificInput = document.querySelector('.specific-pages-input');
            
            if (pagesOption === 'specific') {
                specificInput.style.display = 'block';
            } else {
                specificInput.style.display = 'none';
            }
        });
    });
    
    // تغییر گزینه چندین دسته‌بندی
    document.getElementById('multi_category').addEventListener('change', function() {
        const categoriesContainer = document.querySelector('.categories-container');
        
        if (this.checked) {
            categoriesContainer.style.display = 'block';
        } else {
            categoriesContainer.style.display = 'none';
        }
    });
    
    // ارسال فرم
    document.getElementById('scraper-form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (isRunning) {
            showNotification('یک فرآیند استخراج در حال اجراست. لطفا صبر کنید.', 'warning');
            return;
        }
        
        startScraping();
    });
}

// به‌روزرسانی گزینه‌های دسته‌بندی بر اساس فروشگاه انتخاب شده
function updateCategoriesDropdown(storeType) {
    const categoriesSelect = document.getElementById('categories');
    categoriesSelect.innerHTML = '';
    
    if (storeCategories[storeType]) {
        storeCategories[storeType].forEach(category => {
            const option = document.createElement('option');
            option.value = category.value;
            option.textContent = category.text;
            categoriesSelect.appendChild(option);
        });
        
        // انتخاب اولین گزینه به صورت پیش‌فرض
        if (categoriesSelect.options.length > 0) {
            categoriesSelect.options[0].selected = true;
        }
    }
    
    // به‌روزرسانی URL پیش‌فرض
    if (defaultURLs[storeType]) {
        document.getElementById('url').value = defaultURLs[storeType];
    }
}

// شروع فرآیند استخراج
function startScraping() {
    // جمع‌آوری داده‌های فرم
    const formData = new FormData();
    
    // فروشگاه انتخاب شده
    const storeType = document.querySelector('input[name="store_type"]:checked').value;
    formData.append('store_type', storeType);
    
    // URL
    let url = '';
    if (document.querySelector('input[name="url_type"]:checked').value === 'custom') {
        url = document.getElementById('url').value;
    } else {
        url = defaultURLs[storeType];
    }
    formData.append('url', url);
    
    // تعداد صفحات
    const useMaxPages = document.querySelector('input[name="pages_option"]:checked').value === 'specific';
    formData.append('use_max_pages', useMaxPages);
    
    if (useMaxPages) {
        const maxPages = document.getElementById('max_pages').value;
        formData.append('max_pages', maxPages);
    }
    
    // چندین دسته‌بندی
    const useMultiCategory = document.getElementById('multi_category').checked;
    formData.append('use_multi_category', useMultiCategory);
    
    if (useMultiCategory) {
        const selectedCategories = Array.from(document.getElementById('categories').selectedOptions).map(option => option.value);
        
        if (selectedCategories.length === 0) {
            showNotification('لطفاً حداقل یک دسته‌بندی انتخاب کنید.', 'warning');
            return;
        }
        
        selectedCategories.forEach(category => {
            formData.append('categories[]', category);
        });
    }
    
    // درخواست AJAX برای شروع استخراج
    fetch('/start_scraping', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // نمایش وضعیت استخراج
            isRunning = true;
            updateUI(true);
            
            // شروع بررسی وضعیت
            startStatusPolling();
            
            showNotification('استخراج با موفقیت آغاز شد.', 'success');
        } else {
            showNotification(`خطا: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('خطا در ارتباط با سرور.', 'danger');
    });
}

// شروع بررسی دوره‌ای وضعیت
function startStatusPolling() {
    // ابتدا وضعیت فعلی را دریافت می‌کنیم
    fetchStatus();
    
    // بررسی هر 2 ثانیه
    statusInterval = setInterval(fetchStatus, 2000);
}

// دریافت وضعیت فعلی از سرور
function fetchStatus() {
    fetch('/status')
    .then(response => response.json())
    .then(data => {
        updateStatusUI(data);
        
        // اگر استخراج تمام شده، توقف بررسی
        if (!data.scraper_running && isRunning) {
            isRunning = false;
            updateUI(false);
            clearInterval(statusInterval);
        }
        
        // نمایش اعلان موفقیت
        if (data.show_notification) {
            showNotification(data.notification_message, 'success');
        }
    })
    .catch(error => {
        console.error('Error fetching status:', error);
    });
}

// به‌روزرسانی رابط کاربری بر اساس وضعیت استخراج
function updateStatusUI(data) {
    // به‌روزرسانی پیشرفت
    const progressBar = document.getElementById('progress-bar');
    progressBar.style.width = `${data.progress}%`;
    progressBar.setAttribute('aria-valuenow', data.progress);
    
    // به‌روزرسانی متن پیشرفت
    const progressText = document.getElementById('progress-text');
    if (data.total_pages > 0) {
        progressText.textContent = `استخراج صفحه ${data.current_page} از ${data.total_pages} (${data.progress}%)`;
    } else {
        progressText.textContent = `پیشرفت: ${data.progress}%`;
    }
    
    // به‌روزرسانی وضعیت پیشرفت
    const progressStatus = document.getElementById('progress-status');
    if (data.scraper_running) {
        progressStatus.textContent = 'در حال استخراج...';
        progressStatus.className = 'alert alert-warning';
    } else if (data.progress === 100) {
        progressStatus.textContent = 'استخراج با موفقیت انجام شد!';
        progressStatus.className = 'alert alert-success';
    } else if (data.progress > 0) {
        progressStatus.textContent = 'استخراج متوقف شد.';
        progressStatus.className = 'alert alert-danger';
    }
    
    // به‌روزرسانی لاگ‌ها
    updateLogs(data.logs);
    
    // به‌روزرسانی نتایج
    if (data.product_count > 0) {
        document.getElementById('product-count').textContent = data.product_count;
        document.getElementById('results-container').style.display = 'block';
        
        // به‌روزرسانی جدول محصولات (فقط 20 محصول اول)
        if (data.products && data.products.length > 0) {
            updateProductsTable(data.products.slice(0, 20));
        }
    }
    
    // به‌روزرسانی بخش دانلود
    if (data.output_file) {
        document.getElementById('download-container').style.display = 'block';
        document.getElementById('success-message').textContent = `فایل اکسل با موفقیت ذخیره شد: ${data.output_file}`;
        document.getElementById('excel-download').href = `/download/${data.output_file}`;
    }
}

// به‌روزرسانی لاگ‌ها
function updateLogs(logs) {
    if (!logs || logs.length === 0) return;
    
    const logContainer = document.getElementById('log-container');
    logContainer.innerHTML = '';
    
    logs.forEach(log => {
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        
        // جدا کردن زمان و متن لاگ
        const logParts = log.split(' - ');
        if (logParts.length >= 2) {
            const timeSpan = document.createElement('span');
            timeSpan.className = 'log-time';
            timeSpan.textContent = logParts[0];
            
            const messageSpan = document.createElement('span');
            messageSpan.className = 'log-message';
            messageSpan.textContent = ` - ${logParts.slice(1).join(' - ')}`;
            
            logEntry.appendChild(timeSpan);
            logEntry.appendChild(messageSpan);
        } else {
            logEntry.textContent = log;
        }
        
        logContainer.appendChild(logEntry);
    });
    
    // اسکرول به پایین
    logContainer.scrollTop = logContainer.scrollHeight;
}

// به‌روزرسانی جدول محصولات
function updateProductsTable(products) {
    if (!products) return;
    
    const tableBody = document.querySelector('#products-table tbody');
    tableBody.innerHTML = '';
    
    products.forEach((product, index) => {
        const row = document.createElement('tr');
        
        const numCell = document.createElement('td');
        numCell.textContent = index + 1;
        row.appendChild(numCell);
        
        const nameCell = document.createElement('td');
        nameCell.textContent = product.name;
        row.appendChild(nameCell);
        
        const brandCell = document.createElement('td');
        brandCell.textContent = product.brand;
        row.appendChild(brandCell);
        
        const priceCell = document.createElement('td');
        priceCell.textContent = product.price;
        row.appendChild(priceCell);
        
        const weightCell = document.createElement('td');
        weightCell.textContent = product.weight;
        row.appendChild(weightCell);
        
        const storeCell = document.createElement('td');
        storeCell.textContent = product.store;
        row.appendChild(storeCell);
        
        tableBody.appendChild(row);
    });
}

// به‌روزرسانی رابط کاربری بر اساس وضعیت اجرا
function updateUI(running) {
    if (running) {
        // تغییر وضعیت دکمه استخراج
        document.getElementById('extract-btn-text').textContent = 'در حال استخراج...';
        document.getElementById('extract-spinner').style.display = 'inline-block';
        document.getElementById('extract-btn').disabled = true;
        
        // نمایش نشانگر چرخشی در عنوان وضعیت
        document.getElementById('status-spinner').style.display = 'inline-block';
        document.getElementById('log-spinner').style.display = 'inline-block';
        
        // نمایش بخش پیشرفت
        document.getElementById('initial-status').style.display = 'none';
        document.getElementById('progress-container').style.display = 'block';
    } else {
        // بازگرداندن وضعیت دکمه استخراج
        document.getElementById('extract-btn-text').textContent = 'شروع استخراج';
        document.getElementById('extract-spinner').style.display = 'none';
        document.getElementById('extract-btn').disabled = false;
        
        // پنهان کردن نشانگر چرخشی
        document.getElementById('status-spinner').style.display = 'none';
        document.getElementById('log-spinner').style.display = 'none';
    }
}

// پاک کردن لاگ‌ها
function clearLogs() {
    fetch('/clear_logs', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            document.getElementById('log-container').innerHTML = '<div class="p-3 text-muted">هنوز هیچ لاگی موجود نیست.</div>';
        }
    })
    .catch(error => {
        console.error('Error clearing logs:', error);
    });
}

// نمایش اعلان
function showNotification(message, type = 'success') {
    const toastEl = document.querySelector('.toast');
    const header = toastEl.querySelector('.toast-header');
    const messageEl = document.getElementById('notification-message');
    
    // تنظیم رنگ هدر بر اساس نوع
    header.className = 'toast-header text-white';
    
    if (type === 'success') {
        header.classList.add('bg-success');
        header.querySelector('i').className = 'fas fa-check-circle me-2';
    } else if (type === 'warning') {
        header.classList.add('bg-warning');
        header.querySelector('i').className = 'fas fa-exclamation-triangle me-2';
    } else if (type === 'danger') {
        header.classList.add('bg-danger');
        header.querySelector('i').className = 'fas fa-times-circle me-2';
    }
    
    // تنظیم پیام
    messageEl.textContent = message;
    
    // نمایش اعلان
    toast.show();
} 