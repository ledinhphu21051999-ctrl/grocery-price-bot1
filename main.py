import os
import re
import json
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
from supabase import create_client, Client

# --- 1. KẾT NỐI SUPABASE ---
raw_url = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
if raw_url.endswith("/rest/v1"):
    raw_url = raw_url[:-8].rstrip("/")

SUPABASE_URL = raw_url
SUPABASE_KEY = (os.environ.get("SUPABASE_SECRET_KEY") or "").strip()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. CẤU HÌNH HEADERS VƯỢT TƯỜNG LỬA CHẶN BOT ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1"
}

def fetch_html(url):
    if not url or "http" not in url or "..." in url:
        return None
    try:
        res = cffi_requests.get(url, headers=HEADERS, impersonate="chrome120", timeout=15)
        if res.status_code == 200:
            return res.text
        else:
            print(f"   [!] HTTP {res.status_code} khi tải link")
    except Exception as e:
        print(f"   [!] Lỗi kết nối: {e}")
    return None

def parse_price(text):
    if not text:
        return None
    match = re.search(r'\$?(\d+\.\d{2})', str(text))
    if match:
        val = float(match.group(1))
        if 0.1 <= val <= 200:
            return val
    return None

def scrape_generic_price(url):
    html = fetch_html(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")

    # 1. Thử đọc Walmart __NEXT_DATA__
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data and next_data.string:
        try:
            prices = re.findall(r'"price":\s*(\d+\.\d{2})', next_data.string)
            if prices:
                return float(prices[0])
        except Exception:
            pass

    # 2. Thử đọc Target __TGT_DATA__
    tgt_data = soup.find("script", id="__TGT_DATA__")
    if tgt_data and tgt_data.string:
        try:
            prices = re.findall(r'"current_retail":\s*(\d+\.\d{2})', tgt_data.string)
            if prices:
                return float(prices[0])
        except Exception:
            pass

    # 3. Thử đọc JSON-LD (Aldi / General)
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data = data[0]
            offers = data.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0]
            price = offers.get("price") or offers.get("lowPrice")
            p_val = parse_price(price)
            if p_val:
                return p_val
        except Exception:
            continue

    # 4. Tìm thẻ meta
    for meta_prop in ["product:price:amount", "og:price:amount", "twitter:data1", "price"]:
        meta = soup.find("meta", property=meta_prop) or soup.find("meta", attrs={"name": meta_prop}) or soup.find("meta", itemprop="price")
        if meta and meta.get("content"):
            p_val = parse_price(meta["content"])
            if p_val:
                return p_val

    # 5. Regex quét giá $X.XX
    prices = re.findall(r'\$(\d+\.\d{2})', html)
    if prices:
        valid_prices = [float(p) for p in prices if 0.5 <= float(p) <= 100]
        if valid_prices:
            return valid_prices[0]

    return None

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
# --- 4. HÀM CHẠY CHÍNH ---
def main():
    print("=== BẮT ĐẦU CÀO GIÁ TỰ ĐỘNG ===")
    
    # 1. Cào giá xăng
    gas_price = scrape_aaa_gas()
    print(f"[GAS] Giá xăng trung bình Mỹ: ${gas_price}")
    if gas_price:
        supabase.table("gas_prices").insert({"national_avg": gas_price}).execute()

    # 2. Xóa các hàng NULL cũ trong daily_prices để làm sạch bảng
    try:
        supabase.table("daily_prices").delete().neq("id", 0).execute()
        print("[CLEAN] Đã làm sạch các dòng cũ trong bảng daily_prices")
    except Exception as e:
        print(f"[WARN] Không thể xóa dữ liệu cũ: {e}")

    # 3. Cào và chèn giá mới
    for item in STAPLES_DATA:
        print(f"\n[PRODUCT] Đang cào: {item['name']}")
        w_price = scrape_generic_price(item["walmart"])
        t_price = scrape_generic_price(item["target"])
        a_price = scrape_generic_price(item["aldi"])
        
        print(f" -> Kết quả: Walmart: ${w_price} | Target: ${t_price} | Aldi: ${a_price}")
        
        supabase.table("daily_prices").insert({
            "product_name": item["name"],
            "walmart_price": w_price,
            "target_price": t_price,
            "aldi_price": a_price
        }).execute()

    print("\n=== HOÀN TẤT CẬP NHẬT DỮ LIỆU ===")

if __name__ == "__main__":
    main()
