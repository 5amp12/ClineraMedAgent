#Shared OpenAI client. Insert your key on the line below — every node uses this one client.

from openai import OpenAI

MODEL = "gpt-4o-mini"
client = OpenAI(api_key="API_KEY_HERE")   # <-- insert your OpenAI key here
