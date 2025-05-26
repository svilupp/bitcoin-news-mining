run-scraper-test:
	uv run scripts/web_scraper.py --url https://en.bitcoinwiki.org/wiki/bitcoin-history --max-chunks 10
	uv run scripts/web_scraper.py --url https://en.bitcoin.it/wiki/Category:History --max-chunks 10
	uv run scripts/web_scraper.py --url https://trustmachines.co/bitcoin-history/ --max-chunks 10
	uv run scripts/export_scraped_to_csv.py

run-scraper:
	uv run scripts/web_scraper.py --url https://en.bitcoinwiki.org/wiki/bitcoin-history
	uv run scripts/web_scraper.py --url https://en.bitcoin.it/wiki/Category:History
	uv run scripts/web_scraper.py --url https://trustmachines.co/bitcoin-history/
	uv run scripts/export_scraped_to_csv.py

clean-scraper:
	rm -rf data_raw/scraped/*
	rm -rf data_output/scraped/*
	rm data_processed/scraped_events.csv