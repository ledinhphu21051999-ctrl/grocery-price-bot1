import os
import re
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
from supabase import create_client, Client

# --- 1. TỰ ĐỘNG LÀM SẠCH VÀ CHUẨN HÓA URL SUPABASE ---
raw_url = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
if raw_url.endswith("/rest/v1"):
    raw_url = raw_url[:-8].rstrip("/")

SUPABASE_URL = raw_url
SUPABASE_KEY = (os.environ.get("SUPABASE_SECRET_KEY") or "").strip()

# Kết nối Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# --- 2. CẤU HÌNH HEADERS GIẢ LẬP TRÌNH DUYỆT CHỐNG BỊ CHẶN ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def fetch_html(url):
    """Hàm cào dữ liệu bằng curl_cffi giả lập Chrome"""
    try:
        response = cffi_requests.get(url, headers=HEADERS, impersonate="chrome120", timeout=15)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"[LỖI] Không thể cào link {url}: {e}")
    return None

def extract_price(text):
    """Tách lấy con số giá tiền (VD: '$3.29' -> 3.29)"""
    if not text:
        return None
    match = re.search(r'\$?(\d+\.\d{2})', text)
    return float(match.group(1)) if match else None

# --- 3. HÀM CÀO GIÁ XĂNG TỪ AAA ---
def scrape_aaa_gas():
    url = "https://gasprices.aaa.com/"
    html = fetch_html(url)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if table:
            first_row = table.find("tbody").find("tr") if table.find("tbody") else None
            if first_row:
                cells = first_row.find_all("td")
                if len(cells) >= 2:
                    match = re.search(r'\$?(\d+\.\d{3})', cells[1].text)
                    return float(match.group(1)) if match else None
    return None

# --- 4. HÀM CÀO GIÁ SẢN PHẨM ---
def scrape_generic_price(url):
    if not url or "http" not in url:
        return None
    html = fetch_html(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    
    # Tìm thẻ meta chứa giá tiền
    price_meta = soup.find("meta", property="product:price:amount") or soup.find("meta", itemprop="price")
    if price_meta and price_meta.get("content"):
        return float(price_meta["content"])
    
    # Tìm thẻ chứa thông tin giá
    for el in soup.find_all(class_=re.compile(r'price', re.I)):
        val = extract_price(el.text)
        if val and 0.1 <= val <= 100:
            return val
    return None

# --- 5. DANH SÁCH 10 MÓN THỰC PHẨM (THAY LINK THẬT CỦA BẠN VÀO ĐÂY) ---
STAPLES_DATA = [
    {
        "name": "large white eggs 1 dozen",
        "walmart": "https://www.walmart.com/ip/Great-Value-Cage-Free-Large-White-Eggs-12-Count/421705528?classType=REGULAR&athbdg=L1102&from=/search",
        "target": "https://www.target.com/p/grade-a-large-eggs-12ct-good-38-gather-8482-packaging-may-vary/-/A-14713534",
        "aldi": "https://www.aldi.us/store/aldi/products/115095-goldhen-grade-a-large-eggs-12-ct"
    },
    {
        "name": "Whole Milk 1 Gal",
        "walmart": "https://www.walmart.com/ip/Great-Value-Whole-Vitamin-D-Milk-Gallon-Plastic-Jug-128-Fl-Oz/10450114?classType=REGULAR&athbdg=L1200&from=/search",
        "target": "https://www.target.com/p/milk-good-gather/-/A-94602358?preselect=13276134",
        "aldi": "https://www.aldi.us/store/aldi/products/16902710-friendly-farms-vitamin-d-milk-1-gal"
    },
    {
        "name": "White Bread",
        "walmart": "https://www.walmart.com/ip/Great-Value-White-Round-Top-Bread-Loaf-20-oz/10315355?classType=REGULAR&athbdg=L1102&from=/search",
        "target": "https://www.target.com/p/white-sandwich-bread-20oz-market-pantry-8482/-/A-14930378",
        "aldi": "https://www.aldi.us/store/aldi/products/20946160-l-oven-fresh-white-bread-20-oz"
    },
    {
        "name": "Ground Beef 80/20",
        "walmart": "https://www.walmart.com/ip/80-Lean-20-Fat-Ground-Beef-Chuck-1-lb-Tray-Fresh-All-Natural/479601462?classType=REGULAR&athbdg=L1102&from=/search",
        "target": "https://www.target.com/p/all-natural-80-20-ground-beef-good-gather/-/A-94935371?preselect=13287606",
        "aldi": "https://www.aldi.us/store/aldi/products/19507513-85-lean-ground-beef-chub-16-oz"
    },
    {
        "name": "Boneless Skinless Chicken Breast",
        "walmart": "https://www.walmart.com/ip/Tyson-All-Natural-Fresh-Boneless-Skinless-Chicken-Breasts-1-75-3-0-lb-Tray/50067993?classType=REGULAR&athbdg=L1102&from=/search",
        "target": "https://www.target.com/p/conventional-chicken-breast-small-pack-price-per-lb-good-38-gather-8482/-/A-87544735",
        "aldi": "https://www.aldi.us/store/aldi/products/17771057-chicken-breast-1-per-lb"
    },
    {
        "name": "Bananas",
        "walmart": "https://www.walmart.com/ip/Fresh-Banana-Each/44390948?classType=REGULAR&athbdg=L1200&from=/search",
        "target": "https://www.target.com/p/banana-each-good-38-gather-8482/-/A-15013944",
        "aldi": "https://www.aldi.us/store/aldi/products/25720157-bananas-per-lb"
    },
   {
        "name": "Honeycrisp Apples",
        "walmart": "https://www.walmart.com/ip/Fresh-Honeycrisp-Apple-Each/44390950?classType=REGULAR&athbdg=L1102&from=/search",
        "target": "https://www.target.com/p/honeycrisp-apple-each/-/A-31167786",
        "aldi": "https://www.aldi.us/store/aldi/products/16614400-honeycrisp-apple-each"
    },
    {
        "name": "Cheddar Cheese Block 8 oz",
        "walmart": "https://www.walmart.com/ip/Great-Value-Extra-Sharp-Cheddar-Cheese-8-oz/42004036?classType=REGULAR&from=/search",
        "target": "https://www.target.com/p/cheese-block-good-gather/-/A-95137282?preselect=54340519",
        "aldi": "https://www.aldi.us/store/aldi/products/20752498-happy-farms-sharp-cheddar-cheese-block-8-oz"
    },
    {
        "name": "100% Orange Juice 52 oz",
        "walmart": "https://www.walmart.com/ip/Great-Value-100-Pasteurized-Orange-Juice-with-No-Pulp-52-fl-oz/403284742?classType=VARIANT&athbdg=L1102&from=/search",
        "target": "https://www.target.com/p/100-orange-juice-not-from-concentrate-good-gather/-/A-95004811?preselect=78098807",
        "aldi": "https://www.aldi.us/store/aldi/products/19407400-nature-s-nectar-not-from-concentrate-no-pulp-premium-orange-juice-52-fl-oz"
    },
    {
        "name": "Medium Roast Ground Coffee 12 oz",
        "walmart": "https://www.walmart.com/ip/6-pack-Great-Value-Blueberry-Medium-Roast-Ground-Coffee-12-oz/17091908881?classType=VARIANT&athbdg=L1800&from=/search",
        "target": "https://www.target.com/p/signature-coffee-organic-three-region-blend-medium-roast-ground-coffee-12oz-good-38-gather-8482/-/A-78613369",
        "aldi": "https://www.aldi.us/store/aldi/products/64796015-house-ground-coffee"
    },
]
# --- 6. HÀM CHẠY CHÍNH ĐẨY DỮ LIỆU VÀO SUPABASE ---
def main():
    print("=== BẮT ĐẦU CÀO GIÁ TỰ ĐỘNG ===")
    
    # 1. Cào giá xăng và đẩy vào bảng gas_prices
    gas_price = scrape_aaa_gas()
    print(f"[GAS] Giá xăng trung bình Mỹ: ${gas_price}")
    if gas_price:
        supabase.table("gas_prices").insert({"national_avg": gas_price}).execute()

    # 2. Cào giá 10 món thực phẩm và đẩy vào bảng daily_prices
    for item in STAPLES_DATA:
        print(f"\n[PRODUCT] Đang cào: {item['name']}")
        w_price = scrape_generic_price(item["walmart"])
        t_price = scrape_generic_price(item["target"])
        a_price = scrape_generic_price(item["aldi"])
        
        print(f" -> Walmart: ${w_price} | Target: ${t_price} | Aldi: ${a_price}")
        
        supabase.table("daily_prices").insert({
            "product_name": item["name"],
            "walmart_price": w_price,
            "target_price": t_price,
            "aldi_price": a_price
        }).execute()

    print("\n=== HOÀN TẤT CẬP NHẬT DỮ LIỆU ===")

if __name__ == "__main__":
    main()
