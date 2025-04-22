import requests
import json
import re
from datetime import datetime
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from constants import BONKERS_URLS

class BonkersCornerScraper:
    def __init__(self):
        self.base_url = "https://www.bonkerscorner.com"
        self.seen_products = set()
        self.products = []
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    def run(self):
        print("Starting Bonkers Corner scrape...")
        for category, base_url in BONKERS_URLS.items():
            print(f"Scraping category: {category.replace('_', ' ').title()}")
            self._scrape_category(base_url, category)
        
        self._save_data()
        print(f"Total products scraped: {len(self.products)}")

    def _scrape_category(self, base_url, category):
        page = 1
        while True:
            url = f"{base_url}?page={page}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                break
                
            products = self._extract_products(response.text, category)
            if not products:
                break
                
            self.products.extend(products)
            page += 1
            time.sleep(1)

    def _extract_products(self, html, category):
        soup = BeautifulSoup(html, 'html.parser')
        script_tag = soup.find('script', id='web-pixels-manager-setup')
        
        if not script_tag:
            return []
            
        # Extract JSON data from script
        pattern = r'webPixelsManagerAPI\.publish\("collection_viewed",\s*({.*?})\);'
        match = re.search(pattern, script_tag.string, re.DOTALL)
        
        if not match:
            return []
            
        try:
            data = json.loads(match.group(1))
            return self._process_collection(data['collection'], category)
        except json.JSONDecodeError:
            return []

    def _process_collection(self, collection, category):
        products = []
        product_map = {}
        
        # Group variants by parent product
        for variant in collection['productVariants']:
            product_id = variant['product']['id']
            
            if product_id not in product_map:
                product_map[product_id] = {
                    "id": product_id,
                    "title": variant['product']['title'],
                    "url": urljoin(self.base_url, variant['product']['url']),
                    "category": category,
                    "vendor": variant['product']['vendor'],
                    "variants": [],
                    "images": set()
                }
                
            # Add variant
            product_map[product_id]['variants'].append({
                "variant_id": variant['id'],
                "price": variant['price']['amount'],
                "size": variant['title'],
                "sku": variant['sku']
            })
            
            # Add image
            if variant['image']['src']:
                product_map[product_id]['images'].add(
                    urljoin(self.base_url, variant['image']['src'])
                )
        
        # Convert sets to lists and check duplicates
        for product in product_map.values():
            product['images'] = list(product['images'])
            if product['id'] not in self.seen_products:
                self.seen_products.add(product['id'])
                products.append(product)
                
        return products

    def _save_data(self):
        with open("bonkers_products.json", "w") as f:
            json.dump(self.products, f, indent=2)

if __name__ == "__main__":
    scraper = BonkersCornerScraper()
    scraper.run()