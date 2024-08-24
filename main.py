from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import requests

print("""
______  _____ ______  _____  _     
| ___ \/  __ \| ___ \|_   _|| |    
| |_/ /| /  \/| |_/ /  | |  | |    
| ___ \| |    |    /   | |  | |    
| |_/ /| \__/\| |\ \  _| |_ | |____
\____/  \____/\_| \_| \___/ \_____/
                                   
(breaking copyright infringement laws!)
(For educational reasons ONLY!)
""")

def download_resource(url, directory):
    """Download a resource and save it to the specified directory."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            filename = os.path.basename(urlparse(url).path)
            if not filename:  # Handle URLs that end with '/'
                filename = "index.html"
            filepath = os.path.join(directory, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded {url} to {filepath}")
            return filename
    except Exception as e:
        print(f"Failed to download {url}: {e}")
    return None

def setup_browser():
    """Setup a headless browser instance."""
    options = Options()
    options.add_argument("--headless")  # Run in headless mode (no UI)
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return browser

def download_page(url, visited, directory=None, index=1, download_links=False, browser=None):
    if browser is None:
        browser = setup_browser()

    # Normalize the URL (handle cases with and without trailing slashes)
    url = url.rstrip('/')

    # If no directory is provided, create one based on the domain
    if directory is None:
        domain = urlparse(url).netloc
        directory = domain.replace('.', '_')
    
    # Create directory if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # Check if the URL has already been visited
    if url in visited:
        print(f"Already visited {url}, skipping download.")
        return None
    
    # Mark this URL as visited
    visited.add(url)
    
    print(f"Running scraper with JavaScript enabled on {url}")
    
    # Use Selenium to get the fully rendered page (JavaScript executed)
    browser.get(url)
    html = browser.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    # Save the main HTML file with sequential naming
    html_filename = f"index-{index}.html"
    html_filepath = os.path.join(directory, html_filename)
    with open(html_filepath, 'wb') as f:
        f.write(soup.prettify("utf-8"))
        print(f"HTML saved to {html_filepath}")
    
    # Download and replace CSS files
    for css in soup.find_all('link', {'rel': 'stylesheet'}):
        css_url = urljoin(url, css['href'])
        css_filename = download_resource(css_url, directory)
        if css_filename:
            css['href'] = css_filename
    
    # Download and replace JavaScript files
    for js in soup.find_all('script', {'src': True}):
        js_url = urljoin(url, js['src'])
        js_filename = download_resource(js_url, directory)
        if js_filename:
            js['src'] = js_filename
    
    # Download and replace image files
    for img in soup.find_all('img'):
        img_url = urljoin(url, img['src'])
        img_filename = download_resource(img_url, directory)
        if img_filename:
            img['src'] = img_filename
    
    # Download and replace audio files
    for audio in soup.find_all('audio'):
        if audio.get('src'):
            audio_url = urljoin(url, audio['src'])
            audio_filename = download_resource(audio_url, directory)
            if audio_filename:
                audio['src'] = audio_filename
        for source in audio.find_all('source'):
            audio_url = urljoin(url, source['src'])
            audio_filename = download_resource(audio_url, directory)
            if audio_filename:
                source['src'] = audio_filename
    
    # Replace all href links with the local paths, except for specific domains (e.g., google.com)
    skip_domains = ['google.com']
    
    for link in soup.find_all(['a', 'link'], href=True):
        href = link['href']
        href_url = urljoin(url, href)
        href_domain = urlparse(href_url).netloc
        
        if any(domain in href_domain for domain in skip_domains):
            # Skip replacing hrefs that match the skip domains
            continue
        
        if download_links and (not href.startswith(('http', 'https')) or href_domain == urlparse(url).netloc):
            local_href = download_page(href_url, visited, directory, index=index+1, download_links=download_links, browser=browser)
            if local_href:
                link['href'] = local_href
        else:
            # Handle external links (convert to local if downloaded)
            if href_domain == urlparse(url).netloc:
                local_href = download_resource(href_url, directory)
                if local_href:
                    link['href'] = local_href
    
    # Save the modified HTML with correct local paths
    with open(html_filepath, 'wb') as f:
        f.write(soup.prettify("utf-8"))
        print(f"Modified HTML saved to {html_filepath}")
    
    # Return the local HTML filename for updating hrefs
    return html_filename

if __name__ == "__main__":
    url = input("Enter the URL of the webpage you want to download: ")
    download_links = input("Do you want to download linked pages (hrefs) from this site? (y/n): ").lower() in ['y', 'yes']
    visited_urls = set()  # Initialize a set to keep track of visited URLs
    browser_instance = setup_browser()  # Create a browser instance
    try:
        main_html = download_page(url, visited_urls, download_links=download_links, browser=browser_instance)
        if main_html:
            print(f"\nDownload complete. Main page saved as: {main_html}")
    finally:
        browser_instance.quit()  # Ensure the browser instance is closed when done
