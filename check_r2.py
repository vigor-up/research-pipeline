import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="https://adb1040c847f4ae4a7d6bfedcccd7b77.r2.cloudflarestorage.com",
    aws_access_key_id="f443b2e5acc77dd1af6a83a5d548b35b",
    aws_secret_access_key="da1c377ffbc03b865504e292480e0e2806ddb84a61bf87b7e6a2066632a4a357",
    region_name="auto",
)
resp = s3.list_objects_v2(Bucket="richtrong-collect")
for obj in resp.get("Contents", []):
    print(f"{obj['Key']:60s} {obj['Size']:>10} bytes  {obj['LastModified'].strftime('%Y-%m-%d %H:%M')}")
