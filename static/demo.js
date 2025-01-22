const servicesList = [
    { name: 'openai', logo: 'https://www.openai.com/favicon.ico', displayName: 'OpenAI' },
    { name: 'groq', logo: 'https://groq.com/wp-content/uploads/2024/02/android-icon-192x192-1.png', displayName: 'GroQ' },
    { name: 'sambanova', logo: 'https://www.sambanova.ai/favicon.ico', displayName: 'SambaNova' },
    { name: 'together', logo: 'https://cdn.prod.website-files.com/64f6f2c0e3f4c5a91c1e823a/654693d90fe837461728588f_webclip.png', displayName: 'Together' },
    { name: 'cerebras', logo: 'https://cerebras.ai/wp-content/uploads/2022/05/cropped-cerebras-logo-fav-32x32.png', displayName: 'Cerebras' },
];

// Get URL parameters for services and prompt
const urlParams = new URLSearchParams(window.location.search);
const servicesFromUrl = urlParams.get('services') ? urlParams.get('services').split(',') : [];
const promptFromUrl = urlParams.get('prompt') || '';
const isStreaming = urlParams.get('streaming') === 'true';

// Populate the dropdown and select services from URL parameters
const servicesSelect = document.getElementById('services');
servicesList.forEach(service => {
    const option = document.createElement('option');
    option.value = service.name;
    option.textContent = service.displayName;
    servicesSelect.appendChild(option);
});

// Pre-select services from the URL
servicesFromUrl.forEach(service => {
    const option = servicesSelect.querySelector(`option[value="${service}"]`);
    if (option) {
        option.selected = true;
    }
});

// Refresh the Bootstrap select picker
$('#services').selectpicker('refresh');

// Set the prompt if passed in the URL
document.getElementById('prompt').value = promptFromUrl;
const streamingCheckbox = document.getElementById('streaming');
streamingCheckbox.checked = isStreaming;

document.addEventListener("DOMContentLoaded", function () {
    document.getElementById('inference-form').addEventListener('submit', async function (e) {
        e.preventDefault();

        // Get selected services
        const selectedServices = Array.from(document.getElementById('services').selectedOptions).map(option => option.value);
        const uniqueServices = [...new Set(selectedServices)];
        const prompt = document.getElementById('prompt').value;
        const isStreaming = document.getElementById('streaming').checked;

        // Update URL with selected services and prompt
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.set('prompt', prompt);
        newUrl.searchParams.set('services', uniqueServices.join(','));
        newUrl.searchParams.set('streaming', isStreaming);
        history.pushState({}, '', newUrl);

        const formData = new FormData();

        // Add streaming option if checked
        formData.set('streaming', isStreaming);
		formData.set('prompt', prompt);

        // Handle file upload and convert to Base64
        const fileInput = document.getElementById('fileInput');
        if (fileInput && fileInput.files.length > 0) {
            const file = fileInput.files[0];
            const reader = new FileReader();
            reader.onloadend = function () {
                const base64File = reader.result.split(',')[1]; // Get Base64 string
                const fileExtension = file.name.split('.').pop().toLowerCase(); // Extract file extension
                const fileType = file.type.startsWith('image/') ? 'image' : file.type.startsWith('audio/') ? 'audio' : 'unknown';

                formData.set('fileBase64', base64File);
                formData.set('fileType', fileType);
                formData.set('fileExtension', fileExtension);
                formData.set('fileName', file.name);
                submitFormData(formData);
            };
            reader.readAsDataURL(fileInput.files[0]);
        } else {
            submitFormData(formData);
        }
        
        async function submitFormData(formData) {
            document.getElementById('results').innerHTML = "";
            document.getElementById('loading-indicator').style.display = 'block';
            serviceCode = {}
            let completedRequests = 0;

            const serviceRequests = uniqueServices.map(service => {
                formData.set('service', service);
                serviceCode[service]= undefined;
    
                $.ajax({
                    url: '/infer',
                    type: 'POST',
                    data: formData,
                    contentType: false,
                    processData: false,
                    success: function(data) {
                        if (data && data[service] && data[service].result) {
                            showServiceResults(data);
                            completedRequests++;
                            checkAndHideLoadingIndicator();
                        } else if (data && data.startsWith("data: ")) {
                            processChunk(data, serviceCode, service);
                            completedRequests++;
                            checkAndHideLoadingIndicator();
                        }
                    },
                    xhr: function() {
                        var xhr = new window.XMLHttpRequest();
                        xhr.onreadystatechange = function () {
                            if (xhr.readyState === 3 && xhr.status === 200) {
                                processChunk(xhr.responseText, serviceCode, service);
                            }
                        };
                        return xhr;
                    }
                });
            });
            await Promise.all(serviceRequests);

            function checkAndHideLoadingIndicator() {
                if (completedRequests === uniqueServices.length) {
                    console.log('hiding');
                    $('#loading-indicator').hide();
                    document.getElementById('loading-indicator').style.display = 'none';
                }
            }
        }

        function processChunk(chunkText, serviceCode, service) {
            if (chunkText == "data: [DONE]") {
                return;
            }
            if (!chunkText.startsWith("data: ")) {
                return;
            }
            const chunkDataArray = chunkText.split('data: ').filter(function (chunkData) {
                return chunkData.trim() !== '';
            });
            if (!serviceCode[service]) {
                var output_data = {};
                output_data[service] = {
                    'result': '',
                    'totalTokens': 0,
                    'inputTokens': 0,
                    'outputTokens': 0,
                    'model': '',
                    'timeTaken': 0,
                    'service': service
                };
                showServiceResults(output_data, service);
                serviceCode[service] = {}
                serviceCode[service]['code'] = $(`#result-${service}-text`).get(0);
                serviceCode[service]['code'].innerHTML = "";
                serviceCode[service]['processedLength'] = 0;
            }

            // Process each chunk of data
            let currentLength = 0;
            let previousLength = serviceCode[service]['processedLength'];
            chunkDataArray.forEach(function (chunkData) {
                try {
                    chunkData=chunkData.trim()
                    currentLength+=1;

                    if (currentLength <= previousLength) {
                        return;
                    }
                    if (chunkData == "[DONE]") {
                    } else {
                        try {
                            var data = JSON.parse(chunkData);
                            var content = undefined;                                                
                            if (data.choices && data.choices[0] && data.choices[0].delta && data.choices[0].delta.content) {
                                content = data.choices[0].delta.content;
                            } else if (data.status && data.status == "STREAM_ENDED") {
                                $(`#tokens-${service}-text`).get(0).innerHTML = "0";
                                if (data.model) {
                                    $(`#model-${service}-text`).get(0).innerHTML = `${data.model}`
                                }
                                if (data.timeTaken) {
                                    $(`#time-${service}-text`).get(0).innerHTML = `${data.timeTaken.toFixed(2)}s`
                                }
                            }
                            if (content != undefined) {
                                serviceCode[service]['code'].innerHTML += content;
                                serviceCode[service]['code'].scrollTop = serviceCode.scrollHeight;
                            }
                        } catch(error) {
                            console.error('Error parsing chunk:', error, 'chunk:', chunkData);
                        }
                    }
                } catch (error) {
                    console.error('Error:', error);
                }
            });
            serviceCode[service]['processedLength']=chunkDataArray.length;;
        }
    

        function showServiceResults(result, service_name) {
            // Get the service name from the result
            const service = service_name ? service_name : Object.keys(result)[0];
            const serviceResult = result[service];

			const logoUrl = serviceResult.logo || servicesList.find(s => s.name === service)?.logo;;
			const displayName = serviceResult.displayName || servicesList.find(s => s.name === service)?.displayName;

            // Calculate column size based on the number of services selected
            const totalServices = uniqueServices.length;
            let colSize = 4;  // Default for 3 services
            if (totalServices === 2) {
                colSize = 6;
            } else if (totalServices === 1) {
                colSize = 12;
            }
            // Create the result column
            const resultColumn = document.createElement('div');
            resultColumn.classList.add(`col-md-${colSize}`, 'result-column', 'mt-2', 'mb-2');

            // Create the logo element
            const logo = document.createElement('img');
            logo.src = logoUrl;
            logo.classList.add('inference-logo');
            logo.alt = `${service} Logo`;

            // Create the title (h4)
            const title = document.createElement('h4');
            title.classList.add('text-center');
            title.textContent = displayName;

            // Pre and code elements for result (normal or error)
            const pre = document.createElement('pre');
            const code = document.createElement('code');
            code.id = `result-${service}-text`;
            code.classList.add('result-box');

            let tokensInfo = undefined;
            if (serviceResult.error !== undefined) {
                code.textContent = serviceResult.error;
            } else {
				const markdownContent = marked.parse(serviceResult.result);
				const sanitizedContent = DOMPurify.sanitize(markdownContent);
				code.innerHTML = sanitizedContent;

                // Create tokens info
                tokensInfo = document.createElement('div');
                tokensInfo.classList.add('tokens-info');

                // Time and tokens sections
                const timeTokens = document.createElement('div');
                const timeTokensId = `time-${service}-text`;
                const totalTokensId = `tokens-${service}-text`;
                timeTokens.classList.add('time-tokens');
                timeTokens.innerHTML = `
                    <div><span class="label">Time</span> <span id="${timeTokensId}" class="value">${(serviceResult.timeTaken).toFixed(2)}s</span></div>
                    <div><span class="label">Tokens</span> <span id="${totalTokensId}" class="value">${serviceResult.totalTokens} (input: ${serviceResult.inputTokens}, output: ${serviceResult.outputTokens})</span></div>
                `;
                tokensInfo.appendChild(timeTokens);

                // Model section
                const modelSection = document.createElement('div');
                const modelId = `model-${service}-text`;
                modelSection.classList.add('model');
                modelSection.innerHTML = `
                    <span class="label">Model</span> <span id="${modelId}" class="value">${serviceResult.model}</span>
                `;
                tokensInfo.appendChild(modelSection);
            }
            // Append pre/code to result column
            pre.appendChild(code);

            // Append all parts to the result column
            resultColumn.appendChild(logo);
            resultColumn.appendChild(title);
            if (tokensInfo != undefined) {
                resultColumn.appendChild(tokensInfo);
            }
            resultColumn.appendChild(pre);

            // Append the results row to the main results container
            document.getElementById('results').appendChild(resultColumn);

            // Highlight any code
            hljs.highlightElement(code);
        }
    });
});
