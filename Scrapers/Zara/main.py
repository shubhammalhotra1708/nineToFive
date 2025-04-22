import time
import requests
import json
from urllib.parse import urljoin
from datetime import datetime
from constants import ZARA_URLS

class ZaraScraper:
    def __init__(self):
        self.base_url = "https://www.zara.com"
        self.seen_products = set()
        self.products = []
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        self.total_requests = 0
        self.failed_requests = 0

    def run(self):
        print("🚀 Starting Zara scrape...")
        start_time = time.time()
        
        for category, url in ZARA_URLS.items():
            print(f"\n🔍 Scraping category: {category.replace('_', ' ').title()}")
            self._scrape_category(url, category)
        
        self._save_data()
        print(f"\n✅ Final Results:")
        print(f"   Total Products: {len(self.products)}")
        print(f"   Successful Requests: {self.total_requests}")
        print(f"   Failed Requests: {self.failed_requests}")
        print(f"   Execution Time: {time.time() - start_time:.2f}s")

    def _scrape_category(self, base_url, category):
        page = 1
        max_retries = 3
        consecutive_errors = 0
        
        while True:
            try:
                # Track request metrics
                self.total_requests += 1
                
                print(f"\r   📖 Page {page} | Products: {len(self.products)}", end="", flush=True)
                
                params = {
                    "v1": int(time.time() * 1000),
                    "regionGroupId": "80",
                    "ajax": "true",
                    "page": page
                }
                
                response = None
                for attempt in range(max_retries):
                    try:
                        response = requests.get(base_url, headers=self.headers, params=params)
                        response.raise_for_status()
                        break
                    except requests.exceptions.HTTPError as e:
                        self.failed_requests += 1
                        if e.response.status_code == 404:
                            print(f"\n   🏁 Natural pagination end at page {page}")
                            return
                        print(f"\n   ⚠️ HTTP Error {e.response.status_code} on attempt {attempt+1}")
                        time.sleep(2 ** attempt)
                
                if not response or not response.ok:
                    print("\n   🔴 Max retries exceeded")
                    return
                
                data = response.json()
                
                if not self._validate_response(data):
                    print(f"\n   🚩 Invalid response structure on page {page}")
                    return
                
                new_products = self._extract_products(data, category)
                if not new_products:
                    print(f"\n   ⏹️ No valid products found on page {page}")
                    return
                
                self.products.extend(new_products)
                page += 1
                consecutive_errors = 0
                time.sleep(1.2)
                
            except Exception as e:
                consecutive_errors += 1
                self.failed_requests += 1
                print(f"\n   🔥 Error on page {page}: {str(e)}")
                if consecutive_errors >= 3:
                    print("   🛑 Too many consecutive errors, stopping category")
                    return

    def _validate_response(self, data):
        """Ensure response contains valid product data"""
        if not isinstance(data, dict):
            return False
        if "productGroups" not in data:
            return False
        return any(
            "commercialComponents" in element 
            for group in data["productGroups"] 
            for element in group.get("elements", [])
        )

    def _extract_products(self, data, category):
        products = []
        for group in data.get("productGroups", []):
            for element in group.get("elements", []):
                for component in element.get("commercialComponents", []):
                    if component.get("type") != "Product":
                        continue
                        
                    product_id = str(component.get("id"))
                    if not product_id:
                        print("   🚫 Product missing ID")
                        continue
                        
                    if product_id in self.seen_products:
                        print(f"   ⏭️ Duplicate: {product_id}")
                        continue
                        
                    product_url = self._build_product_url(component)
                    if not product_url:
                        print(f"   🔗 Missing URL for {product_id}")
                        continue
                        
                    product_data = {
                        "id": product_id,
                        "name": component.get("name", "Unnamed Product"),
                        "price": self._parse_price(component.get("price")),
                        "category": category,
                        "url": product_url,
                        "images": self._extract_images(component),
                        "timestamp": datetime.now().isoformat(),
                        # "vendor" : "Zara",
                    }
                    
                    self.seen_products.add(product_id)
                    products.append(product_data)
        return products

    def _build_product_url(self, component):
        """Safely construct product URL"""
        try:
            seo = component.get("seo", {})
            return urljoin(
                self.base_url,
                f"/in/en/{seo['keyword']}-p{seo['seoProductId']}.html"
            )
        except (KeyError, TypeError):
            return None

    def _parse_price(self, price):
        """Convert price from cents to rupees"""
        try:
            return price / 100 if price else None
        except TypeError:
            return None
        
    def _extract_images(self, component):
        """Extract all unique image URLs"""
        images = set()
        for color in component.get("detail", {}).get("colors", []):
            for media in color.get("xmedia", []):
                try:
                    img_url = media['url'].replace("{width}", "1024")
                    images.add(img_url)
                except KeyError:
                    continue
        return list(images)

    def _save_data(self):
        """Save with pretty formatting and backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"zara_products_{timestamp}.json"
        
        try:
            with open(filename, "w") as f:
                json.dump(self.products, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Data saved to {filename}")
        except Exception as e:
            print(f"\n❌ Failed to save data: {str(e)}")

if __name__ == "__main__":
    scraper = ZaraScraper()
    scraper.run()