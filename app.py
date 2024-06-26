from flask import Flask, jsonify, request
from flask_cors import CORS
from PIL import Image
from io import BytesIO
from google.oauth2 import service_account
from google.cloud import vision
import ingredient_data
import os
import json
import base64


app = Flask(__name__)
CORS(app)

def get_vision_client():
    # Decode the environment variable into JSON
    credentials_base64 = os.getenv('GOOGLE_CREDENTIALS_BASE64')
    if credentials_base64 is None:
        raise Exception("Google Cloud credentials not found in environment variables.")
    
    credentials_json = base64.b64decode(credentials_base64)
    credentials_dict = json.loads(credentials_json)
    
    # Authenticate with the Google Cloud Vision API using decoded credentials
    credentials = service_account.Credentials.from_service_account_info(credentials_dict)
    client = vision.ImageAnnotatorClient(credentials=credentials)
    return client

def process_image(image_bytes):
    client = get_vision_client()  # Use the authenticated client
    image = vision.Image(content=image_bytes)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    result_string = texts[0].description if texts else ""
    return result_string


def find_matches(result_string, setting):
    selected_list = getattr(ingredient_data, setting, [])
    result_highlight = set()
    
    for phrase in selected_list:
        if phrase in result_string:
            result_highlight.add(phrase)
    return result_highlight

@app.route("/upload-image", methods=["POST"])
def upload_image():
    if "image" not in request.files:
        return jsonify({"error": "No image part in the request"}), 400
    file = request.files["image"]
    setting = request.form['activeSetting']
    if file.filename == "":
        return jsonify({"error": "No image selected for uploading"}), 400

    image_bytes = file.read()
    if file:
        try:
            image = Image.open(BytesIO(image_bytes))
            rotated_image = image.rotate(-90, expand=True)  
            rotated_image_bytes = BytesIO()
            rotated_image.save(rotated_image_bytes, format=image.format)
            rotated_image_bytes = rotated_image_bytes.getvalue()
            result_string = process_image(rotated_image_bytes).lower()
            result_highlighted = find_matches(result_string, setting)
            return jsonify({"message": "Image successfully processed", "result": result_string, "result_highlights": list(result_highlighted)}), 200
        except Exception as e:  
            return jsonify({"error": "Error processing the image", "details": str(e)}), 400
    else:
        return jsonify({"error": "No file submitted"}), 400

if __name__ == "__main__":
    app.run(debug=True)
    #app.run(debug=True, host='0.0.0.0', port=5000)
