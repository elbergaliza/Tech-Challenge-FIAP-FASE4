from openai import OpenAI

client = OpenAI(
    base_url="https://api.brainiall.com/v1",
    api_key="brnl-c56575def1d7e2828e43a097f9613debbf256361a5dc3e31",
)
response = client.chat.completions.create(
    model="claude-haiku-4-5",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
