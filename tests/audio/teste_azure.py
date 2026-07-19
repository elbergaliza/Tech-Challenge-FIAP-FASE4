import httpx

resp = httpx.post(
    "https://api.brainiall.com/v1/nlp/toxicity",
    headers={
        "Authorization": "Bearer brnl-c56575def1d7e2828e43a097f9613debbf256361a5dc3e31"},
    json={"text": "Hello world"},
)
print(resp.json())
# {"is_toxic": false, "score": 0.001, "label": "not_toxic"}
