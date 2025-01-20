from flask import Flask, render_template, request, jsonify
import os
import aiohttp
import asyncio
import logging
from dotenv import load_dotenv
import time
import json

# Setup logging
logging.basicConfig(format="%(asctime)s %(levelname)s - %(message)s [%(filename)s:%(lineno)d]", level=logging.DEBUG)
logger = logging.getLogger('stcdemo')

# Load environment variables from .env file
load_dotenv()

# Load the models configuration
with open('models_config.json') as f:
    models_config = json.load(f)

# Initialize the Flask app
app = Flask(__name__)

class BaseInfer():
    def __init__(self, service, apikey=None, base_url=None):
        self.service = service
        self.apikey = apikey if apikey is not None else self.get_apikey(service)
        self.modelname = None
        self.base_url = base_url if base_url is not None else self.apibase(service)

    def get_apikey(self, service):
        keyname = service.upper() + "_API_KEY"
        apikey = os.getenv(keyname)
        if apikey is None:
            raise Exception(f"Missing APIKEY {keyname} from environment for {service}")
        return apikey

    def apibase(self, service):
        if service == 'sambanova':
            return 'https://api.sambanova.ai/v1/chat/completions'
        elif service == 'together':
            return 'https://api.together.ai/v1/chat/completions'
        elif service == 'cerebras':
            return 'https://api.cerebras.ai/v1/chat/completions'
        elif service == 'groq':
            return 'https://api.groq.com/openai/v1/chat/completions'
        else:
            return 'https://api.openai.com/v1/chat/completions'

    async def send_request(self, prompt_message, file_data=None):
        try:
            if self.service not in models_config:
                return {'error': f"ERROR: Service {self.service} missing from models_config", 'service': self.service}
            
            payload_message = None

            # Determine which model to use based on file type
            if file_data and 'file_base64' in file_data and file_data['file_base64'] is not None:
                file_type = file_data['file_type']
                file_ext  = file_data['file_ext']
                file_base64 = file_data['file_base64']
                
                if file_type == 'image':
                    self.modelname = models_config[self.service].get("visionModel")
                    payload_message = [
                      {
                          "type" : "text",
                          "text" : prompt_message
                      },
                      {
                          "type" : "image_url",
                          "image_url" : {
                              "url": f"data:image/{file_ext};base64,{file_base64}" 
                          }
                      }
                    ]
                elif file_type == 'audio':
                    self.modelname = models_config[self.service].get("audioModel")
                    payload_message = [
                      {
                          "type" : "text",
                          "text" : prompt_message
                      },
                      {
                          "type" : "audio_url",
                          "audio_url" : {
                              "url": f"data:audio/{file_ext};base64,{file_base64}"
                          }
                      }
                    ]
                else:
                    self.modelname = models_config[self.service].get("textModel")
            else:
                self.modelname = models_config[self.service].get("textModel")

            if self.modelname is None or self.modelname == '':
                return {'error': 'ERROR: Missing Model/Unsupported', 'service': self.service}
            
            if prompt_message is None or prompt_message == '':
                return {'error': 'ERROR: Invalid prompt', 'service': self.service}
            
            headers = {
                'Authorization': f'Bearer {self.apikey}',
                'Content-Type': 'application/json'
            }
            payload_message = prompt_message if payload_message is None else payload_message

            payload = {
                "model": self.modelname,
                "messages" : [{
                    "role" : "user",
                    "content" : payload_message
                }]
            }

            logger.debug(f"[{self.service}] Sending to {self.base_url} with model {self.modelname}")
            logger.info(payload)

            # Record the start time for request
            start_time = time.time()

            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload, headers=headers) as response:
                    response_data = await response.json()
                    time_taken = time.time() - start_time
                    logger.info(f"[{self.service}] Response time: {time_taken:.2f}s")
                    logger.debug(f"[{self.service}]{response_data}")

                    # Prepare output data
                    if 'error' in response_data: 
                        output_data = {
                            'result': response_data['error']['message'],
                            'totalTokens': 0,
                            'inputTokens': 0,
                            'outputTokens': 0,
                            'model': self.modelname,
                            'timeTaken': time_taken,
                            'service': self.service
                        }
                    else:
                        output_data = {
                            'result': response_data['choices'][0]['message']['content'],
                            'totalTokens': response_data['usage']['total_tokens'],
                            'inputTokens': response_data['usage']['prompt_tokens'],
                            'outputTokens': response_data['usage']['completion_tokens'],
                            'model': self.modelname,
                            'timeTaken': time_taken,
                            'service': self.service
                        }

                    return output_data

        except Exception as e:
            logger.error(f"[{self.service}] Error: {str(e)}")
            return {'error': f'[Error from {self.service}] {str(e)}', 'service': self.service}


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/services', methods=['GET'])
async def services():
    services = list(models_config.keys())
    return jsonify({"services": services})

async def process_request(service, prompt, file_data=None):
    return await BaseInfer(service).send_request(prompt, file_data)

# POST handler for a single service
@app.route('/infer', methods=['POST'])
async def infer():
    service = request.form.get('service')  
    prompt = request.form.get('prompt')
    
    base64_file = request.form.get('fileBase64')
    file_ext = request.form.get('fileExtension')
    file_type = request.form.get('fileType')

    if base64_file:
        file_data = {
            'file_type': file_type,
            'file_ext': file_ext,
            'file_base64': base64_file,
        }
    else:
        file_data = None

    if not prompt:
        return jsonify({"error": "Prompt is required."}), 400
    
    output_data={}
    output_data[service]= await process_request(service, prompt, file_data)
    return jsonify(output_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
