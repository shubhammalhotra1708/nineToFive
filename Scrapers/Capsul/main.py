import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from constants import URLS
from green_cargos.services.shared.utils import random_useragent

class CapsulScraper:
    def __init__(self):
        self.base_url = "https://www.shopcapsul.com"
        self.seen_ids = set()
        self.products = []
        self.headers = {
            "User-Agent": random_useragent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        
        # Load existing products
        self._load_existing_data()

    def run(self):
        print("Starting Capsul scrape...")
        for category, url in URLS.items():
            print(f"Scraping category: {category.replace('_', ' ').title()}")
            self._scrape_collection(url, category)
        
        self._save_data()
        print(f"Total products scraped: {len(self.products)}")

    def _scrape_collection(self, url, category):
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        scripts = soup.find_all('script', type='application/ld+json', attrs={'tt-ninja': True})
        
        for script in scripts:
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'ItemList':
                    self._process_itemlist(data['itemListElement'], category)
            except json.JSONDecodeError:
                continue

    def _process_itemlist(self, items, category):
        for item in items:
            product_id = self._extract_product_id(item['url'])
            if product_id in self.seen_ids:
                continue
                
            self.seen_ids.add(product_id)
            
            self.products.append({
                "id": product_id,
                "name": self._clean_html_entities(item['name']),
                "url": urljoin(self.base_url, item['url']),
                "description": self._clean_html_entities(item['description']),
                "image": urljoin(self.base_url, item['image']),
                "position": item['position'],
                "category": category,
                "price": self._extract_price(item['description'])
            })

    def _load_existing_data(self):
        """Load previously scraped products"""
        try:
            with open("products.json", "r") as f:
                existing = json.load(f)
                self.products = existing
                self.seen_ids = {p["id"] for p in existing}
        except FileNotFoundError:
            pass

    def _save_data(self):
        """Save all products to single file"""
        with open("products.json", "w") as f:
            json.dump(self.products, f, indent=2)

    # Keep existing helper methods:
    def _extract_product_id(self, url):
      """Extract unique ID from product URL"""
      return url.split('/')[-1].split('?')[0]

    def _clean_html_entities(self, text):
        """Convert HTML entities to normal text"""
        return (text.replace("&#39;", "'")
                  .replace("&amp;", "&")
                  .replace("&quot;", '"')
                  .strip())

    def _extract_price(self, description):
        """Example of price extraction from description"""
        # This would need custom logic based on actual data patterns
        # For now returns None as price not in structured data
        return None

    def _save_data(self):
        with open("capsul_products.json", "w") as f:
            json.dump(self.products, f, indent=2)
    # _extract_product_id, _clean_html_entities, _extract_price

if __name__ == "__main__":
    scraper = CapsulScraper()
    scraper.run()
