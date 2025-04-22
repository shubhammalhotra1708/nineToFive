import requests
import time
import json
import os
from datetime import datetime
from green_cargos.services.shared.utils import random_useragent

class SnitchScraper:
    def __init__(self):
        self.base_url = "https://www.snitch.com"
        self.api_endpoint = "https://mxemjhp3rt.ap-south-1.awsapprunner.com/products/new-and-popular/v2"
        self.default_limit = 50  # API's maximum allowed limit
        self.current_page = 1
        self.total_products = 0
        self.fetched_products = 0
        self.seen_ids = set()
        
        # Initialize data storage
        self.all_products = []
        self.processed_data = []
        
        # File management
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.raw_filename = f"snitch_raw_{self.timestamp}.json"
        self.processed_filename = f"snitch_processed_{self.timestamp}.json"
        
        self.headers = {
            "User-Agent": random_useragent(),
            "Accept": "application/json",
            "Referer": f"{self.base_url}/"
        }

    def run(self):
        """Main execution flow with proper pagination"""
        print("Starting Snitch scrape...")
        self._load_existing_data()
        
        while True:
            response = self._fetch_page()
            if not response or not response.get("data", {}).get("products"):
                break
                
            data = response["data"]
            products = data["products"]
            
            # Filter new products
            new_products = [
                p for p in products 
                if p["shopify_product_id"] not in self.seen_ids
            ]
            
            if not new_products:
                print("\nReached end of new products. Stopping.")
                break
                
            self._process_products(new_products)
            self._update_progress(len(new_products), data["total_count"])
            
            # Check if we've fetched all available products
            if self.fetched_products >= data["total_count"]:
                break
                
            self.current_page += 1
            time.sleep(0.5)
            
        self._save_data()
        print(f"\nScraped {self.fetched_products}/{self.total_products} products")

    def _fetch_page(self):
        """Fetch a single page of products"""
        try:
            response = requests.get(
                self.api_endpoint,
                headers=self.headers,
                params={
                    "page": self.current_page,
                    "limit": self.default_limit
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Failed to fetch page {self.current_page}: {str(e)}")
            return None

    def _load_existing_data(self):
        """Load previous data to continue scraping"""
        try:
            # Load all JSON files in directory
            for fname in os.listdir():
                if fname.startswith("snitch_processed") and fname.endswith(".json"):
                    with open(fname, "r") as f:
                        data = json.load(f)
                        for item in data:
                            self.seen_ids.add(item["id"])
                            self.total_products = max(self.total_products, item.get("total_count", 0))
        except FileNotFoundError:
            pass

    def _process_products(self, products):
      for product in products:
          processed = {
              "id": product["shopify_product_id"],
              "title": product["title"],
              # Added all requested fields
              "selling_price": product.get("selling_price"),
              "short_description": product.get("short_description"),
             "color": self._parse_color_string(product.get("color")),
              "occassion": product.get("occassion"),  # Note the double 'c' in API
              "model_info": product.get("model_info"),
              # Existing fields
              "url": f"{self.base_url}/products/{product['handle']}",
              "colors": product["colors"],  # Color options array
              "main_image": product["preview_image"],
              "category": product["shopify_product_type"],
              "scraped_at": datetime.now().isoformat(),
              "total_count": product.get("total_count", 0)
          }
          self.seen_ids.add(processed["id"])
          self.fetched_products += 1
          self.processed_data.append(processed)
    def _parse_color_string(self, color_str):
      """Convert "['Beige']" → ["Beige"]"""
      if not color_str:
          return []
      return [c.strip(" '") for c in color_str.strip("[]").split(",")]
    def _update_progress(self, new_count, total_count):
        """Display real-time progress"""
        self.total_products = max(self.total_products, total_count)
        progress = min((self.fetched_products / self.total_products) * 100, 100)
        print(f"Page {self.current_page}: +{new_count} products | Total: {self.fetched_products}/{self.total_products} ({progress:.1f}%)", end="\r")

    def _save_data(self):
        """Save data with incremental naming"""
        with open(self.raw_filename, "w") as f:
            json.dump(self.all_products, f, indent=2)
            
        with open(self.processed_filename, "w") as f:
            json.dump(self.processed_data, f, indent=2)

if __name__ == "__main__":
    scraper = SnitchScraper()
    scraper.run()