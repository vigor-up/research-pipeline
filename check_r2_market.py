import boto3, json

s3 = boto3.client(
    "s3",
    endpoint_url="https://adb1040c847f4ae4a7d6bfedcccd7b77.r2.cloudflarestorage.com",
    aws_access_key_id="f443b2e5acc77dd1af6a83a5d548b35b",
    aws_secret_access_key="da1c377ffbc03b865504e292480e0e2806ddb84a61bf87b7e6a2066632a4a357",
    region_name="auto",
)
obj = s3.get_object(Bucket="richtrong-collect", Key="market_data/latest.json")
data = json.loads(obj["Body"].read())
print("Top-level keys:", list(data.keys()))
print("market_kpi_total:", data.get("market_kpi_total"))
print("competitor_total:", data.get("competitor_total"))
kpi = data.get("market_kpi", [])
print(f"market_kpi sample ({len(kpi)} records):")
for r in kpi[:3]:
    print(" ", r)
