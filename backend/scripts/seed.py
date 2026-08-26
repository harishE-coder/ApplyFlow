"""
ApplyFlow Database Seeding Script.
"""
import asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from seed import seed_database

if __name__ == "__main__":
    asyncio.run(seed_database())
