#Shared OpenAI client — every node uses this one client.
#
#The key comes from OPENAI_API_KEY in .env (gitignored), NOT hardcoded here: this file is
#committed and shared, and a live key in source leaks on the first push.

from __future__ import annotations

import os

from app import config  # noqa: F401  — imported for its side effect: loads .env
from openai import OpenAI

MODEL = "gpt-4o-mini"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
