from flask import Flask, render_template, request, jsonify, Response
import os
import aiohttp
import asyncio
import logging
import traceback
from dotenv import load_dotenv
import time
import json

# Setup logging
logging.basicConfig(format="%(asctime)s %(levelname)s - %(message)s [%(filename)s:%(lineno)d]", level=logging.INFO)
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
    
    def modelname(self):
        return self.modelname

    def apibase(self, service):
        if service in models_config and 'apiBase' in models_config[service]:
            return models_config[service]['apiBase']
        return 'https://api.openai.com/v1/chat/completions'
    
    def setup_payload(self, prompt_message, file_data=None, streaming=False):
        payload_message = None

        self.prompt = prompt_message

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
        
        payload_message = prompt_message if payload_message is None else payload_message
        
        self.headers = {
            'Authorization': f'Bearer {self.apikey}',
            'Content-Type': 'application/json'
        }

        self.payload = {
            "model": self.modelname,
            "stream" : streaming,
            "messages" : [{
                "role" : "user",
                "content" : payload_message
            }]
        }

    async def send_request(self):
        try:
            logger.info(f"[{self.service}]Sending request {self.prompt}")
            if self.service not in models_config:
                return {'error': f"ERROR: Service {self.service} missing from models_config", 'service': self.service}
            
            if self.modelname is None or self.modelname == '':
                return {'error': 'ERROR: Missing Model/Unsupported', 'service': self.service}

            # Record the start time for request
            start_time = time.time()

            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=self.payload, headers=self.headers) as response:
                        response_data = await response.json()
                        time_taken = time.time() - start_time
                        logger.info(f"[{self.service}]Total time {time_taken:,.2}s")
                        
                        # Prepare output data
                        if 'error' in response_data:
                            output_data = {
                                'result': response_data['error']['message'],
                                'totalTokens': 0,
                                'inputTokens': 0,
                                'outputTokens': 0,
                                'model': self.modelname,
                                'timeTaken': time_taken,
                                'service': self.service,
                                'displayName': models_config[self.service]['displayName'],
                                'logo': models_config[self.service]['logo']
                            }
                        else:
                            output_data = {
                                'result': response_data['choices'][0]['message']['content'],
                                'totalTokens': response_data['usage']['total_tokens'],
                                'inputTokens': response_data['usage']['prompt_tokens'],
                                'outputTokens': response_data['usage']['completion_tokens'],
                                'model': self.modelname,
                                'timeTaken': time_taken,
                                'service': self.service,
                                'displayName': models_config[self.service]['displayName'],
                                'logo': models_config[self.service]['logo']
                            }
                        return output_data

        except Exception as e:
            logger.error(f"[{self.service}] Error: {str(e)}")
            return {'error': f'[Error from {self.service}] {str(e)}', 'service': self.service}
        
    def send_stream_request(self):    
        logger.info(f"[{self.service}]Sending stream request {self.prompt}")
        start_time = time.time()

        async def stream():    
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=self.payload, headers=self.headers) as response:
                    async for chunk in response.content.iter_any():
                        chunk_str=chunk.decode('utf-8')
                        yield chunk_str


        def sync_gen():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async_generator = stream()

            try:
                while True:
                    chunk = loop.run_until_complete(async_generator.__anext__())
                    yield chunk

            except StopAsyncIteration:
                final_chunk = {}
                final_chunk['status']="STREAM_ENDED"
                final_chunk['model']=self.modelname
                time_taken = time.time() - start_time
                final_chunk['timeTaken'] = time_taken
                logger.info(f"[{self.service}]Total time {time_taken:,.2}s")
                yield f"data: {json.dumps(final_chunk)}\n\n"
                pass
        return sync_gen()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/services', methods=['GET'])
async def services():
    services = list(models_config.keys())
    return jsonify({"services": services})

async def process_nonstream(payload):
    base = BaseInfer(payload['service'])
    base.setup_payload(payload['prompt'], payload.get('file_data'), False)
    return await base.send_request()

def process_stream(payload):
    base = BaseInfer(payload['service'])
    base.setup_payload(payload['prompt'], payload.get('file_data'), True)
    return base.send_stream_request()

# POST handler for a single service with optional streaming
@app.route('/infer', methods=['POST'])
async def infer():
    try:
        service = request.form.get('service')  
        prompt = request.form.get('prompt')
        file_data = None
        
        base64_file = request.form.get('fileBase64')
        file_ext = request.form.get('fileExtension')
        file_type = request.form.get('fileType')

        streaming = request.form.get('streaming') == 'true'

        if base64_file is not None and base64_file != '':
            file_data = {
                'file_type': file_type,
                'file_ext': file_ext,
                'file_base64': base64_file,
            }

        if not prompt:
            return jsonify({"error": "Prompt is required.", "service": service}), 400

        if not service and service == '':
            return jsonify({"error": "Missing/Invalid service name."}), 400
        
        payload = {'service': service, 'prompt': prompt, 'file_data': file_data}
        
        if streaming:
            return Response(process_stream(payload), mimetype='text/event-stream')
        else:
          data = await process_nonstream(payload)
          output_data = {}
          output_data[service] = data
          return jsonify(output_data)
    except Exception as e:
        logger.error(e)
        traceback.print_exc()
        return jsonify({"error": f"{str(e)}", "service": service}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
