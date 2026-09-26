"""Exercise PostgreSQL-backed Skill source and registry extension points."""

from __future__ import annotations

import asyncio

from _postgres import main

if __name__ == "__main__":
    asyncio.run(main())
