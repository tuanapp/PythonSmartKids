import base64
import json

#1
data = {
  "type": "service_account",
  "project_id": "smartboy-460011",
  "private_key_id": "",
  "private_key": "",
  "client_email": "smartboy-billing@smartboy-460011.iam.gserviceaccount.com",
  "client_id": "",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/smartboy-billing%40smartboy-460011.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}


json_str = json.dumps(data)
encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
print(encoded)
