import json
import time
import base64
import string
import argparse
import os
from random import randint, choices
try:
    import requests
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad, pad
except ImportError:
    print("Please install required packages: pip install pycryptodome requests")
    exit(1)

# AES Keys for the V1 API
keys = [
    "oppo1997", "baed2017", "java7865", "231uiedn", "09e32ji6",
    "0oiu3jdy", "0pej387l", "2dkliuyt", "20odiuye", "87j3id7w"
]

def get_key(key: str) -> bytes:
    one = keys[int(key[0])]
    two = key[4:12]
    return (one + two).encode('UTF8')

def generate_key_pseudo() -> str:
    key_id = str(randint(0, 9))
    key = ''.join(choices(string.ascii_letters + string.digits, k=14))
    return key_id + key

def encrypt(data_plain: str) -> str:
    key_pseudo = generate_key_pseudo()
    key_real = get_key(key_pseudo)
    cipher = AES.new(key_real, AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(data_plain.encode('UTF8'), AES.block_size))
    return base64.b64encode(encrypted).decode('UTF8') + key_pseudo

def decrypt(data_encrypted: str) -> str:
    data = base64.b64decode(data_encrypted[:-15])
    key = get_key(data_encrypted[-15:])
    cipher = AES.new(key, AES.MODE_ECB)
    plain = unpad(cipher.decrypt(data), AES.block_size)
    return plain.decode('UTF8')

def query_update(model: str, ota_version: str, region: str = "CN", is_beta: bool = False, output_url_only: bool = False):
    if not output_url_only:
        print(f"\n[*] Querying OTA for {model} (Version: {ota_version}, Region: {region}) ...")
    
    url = 'https://iota.coloros.com/post/Query_Update'
    if region == "GL":
        url = 'https://ifota.realmemobile.com/post/Query_Update'
    elif region == "IN":
        url = 'https://ifota-in.realmemobile.com/post/Query_Update'
    elif region == "EU":
        url = 'https://ifota-eu.realmemobile.com/post/Query_Update'

    headers = {
        'User-Agent': 'com.oneplus.opbackup/2.1.1.190915111124.7ae7e68',
        'Content-Type': 'application/json'
    }
    
    body = {
        "version": "2",
        "otaVersion": ota_version,
        "imei": "000000000000000",
        "mode": "1" if is_beta else "0",
        "language": "zh-CN" if region == "CN" else "en-US",
        "productName": model,
        "type": "1",
        "romVersion": ota_version,
        "colorOSVersion": "UNKNOWN",
        "androidVersion": "14",
        "time": int(time.time() * 1000.0),
        "registrationId": "UNKNOWN",
        "operator": "UNKNOWN",
        "operator2": "UNKNOWN",
        "trackRegion": region,
        "uRegion": region,
        "isRooted": "0",
        "isOnePlus": "1" if "P" in model else "0",
        "canCheckSelf": "0"
    }

    try:
        response = requests.post(url, json={'params': encrypt(json.dumps(body))}, headers=headers, timeout=30)
        
        if response.status_code == 200:
            response_body = response.json()
            
            if response_body.get("responseCode") == 304:
                if not output_url_only:
                    print("[-] Server returned 304 (No Update Found).")
                if not ota_version.endswith("0001_000000000001"):
                    if not output_url_only:
                        print("[*] Automatically retrying with fallback '0001_000000000001' suffix...")
                    if "_" in ota_version:
                        fallback_version = ota_version.rsplit('_', 1)[0] + "_0001_000000000001"
                    else:
                        fallback_version = ota_version + "_0001_000000000001"
                    query_update(model, fallback_version, region, is_beta, output_url_only)
                return

            if "resps" in response_body:
                response_obj = json.loads(decrypt(response_body['resps']))
                
                download_urls = []
                if "components" in response_obj:
                    for comp in response_obj["components"]:
                        if "componentPackets" in comp:
                            packets = comp["componentPackets"]
                            url_val = packets.get("manualUrl") or packets.get("url")
                            if url_val:
                                download_urls.append(url_val)
                elif "url" in response_obj:
                    download_urls.append(response_obj["url"])

                if output_url_only:
                    if download_urls:
                        # Output the first URL found (usually the full package or manifest)
                        print(download_urls[0])
                        # Set Github Action output if env var exists
                        if os.getenv('GITHUB_OUTPUT'):
                            with open(os.getenv('GITHUB_OUTPUT'), 'a') as f:
                                f.write(f"ota_url={download_urls[0]}\n")
                else:
                    print("\n[+] Update Found!")
                    for u in download_urls:
                        print(f"Download URL: {u}")
                    print("\n[+] Raw JSON:")
                    print(json.dumps(response_obj, indent=4, ensure_ascii=False))
            else:
                if not output_url_only:
                    print("\n[?] Unknown Response:")
                    print(json.dumps(response_body, indent=4, ensure_ascii=False))
        else:
            if not output_url_only:
                print(f"[-] HTTP {response.status_code}: {response.text}")

    except Exception as e:
        if not output_url_only:
            print(f"[-] Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find OnePlus/Oppo/Realme OTA Updates")
    parser.add_argument("-m", "--model", help="Device model (e.g., PJD110, CPH2581)")
    parser.add_argument("-v", "--version", help="Current OTA version (e.g., PJD110_14.0.0.840(CN01))")
    parser.add_argument("-r", "--region", choices=["CN", "GL", "IN", "EU"], default="CN", help="Region (default: CN)")
    parser.add_argument("-b", "--beta", action="store_true", help="Check for beta updates")
    parser.add_argument("--url-only", action="store_true", help="Only output the OTA download URL (for scripting/CI)")
    
    args = parser.parse_args()
    
    if args.model and args.version:
        query_update(args.model, args.version, args.region, args.beta, args.url_only)
    else:
        print("=== Oplus OTA Finder CLI ===")
        model = input("Enter device model (e.g. PJD110): ").strip()
        version = input("Enter current OTA version (e.g. PJD110_14.0.0.840(CN01)): ").strip()
        region = input("Enter region [CN/GL/IN/EU] (default CN): ").strip().upper() or "CN"
        is_beta = input("Check for beta updates? [y/N]: ").strip().lower() == 'y'
        
        if model and version:
            query_update(model, version, region, is_beta, False)
        else:
            print("Model and Version are required!")
