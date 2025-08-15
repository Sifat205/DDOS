# SM DDOS Stress Testing Tool

An advanced Python-based tool for ethical HTTP stress-testing to evaluate website resilience. Optimized for Termux/VPS.

## Usage
Run: `python3 ddos.py`
- Follow prompts to enter URL and request count.
- Example: `https://sm5test.rf.gd/SM/sm-bomber.html`, 10000 requests, 100 req/s.

## Prerequisites
- Python 3.7+
- Libraries: `pip install aiohttp psutil`

## Warning
For authorized use only. Unauthorized testing is illegal. Logs saved to `ddos_test.log`.

## Configuration
Edit `CONFIG` in `ddos.py` to adjust `max_requests`, `request_rate`, `batch_size`, etc.
