using McpImage2ImageCs.Settings;
using Microsoft.Extensions.Options;
using System.Net;
using System.Net.Http.Headers;
using System.Text.Json;

namespace McpImage2ImageCs.Services;

public class FoundryClient
{
    private readonly HttpClient _httpClient;
    private readonly FoundrySettings _settings;
    private readonly ILogger<FoundryClient> _logger;

    public FoundryClient(
        IHttpClientFactory httpClientFactory, 
        IOptions<FoundrySettings> settings, 
        ILogger<FoundryClient> logger)
    {
        _httpClient = httpClientFactory.CreateClient("FoundryClient");
        _settings = settings.Value;
        _logger = logger;
    }

    public async Task<byte[]> EditImageAsync(
        string originalImageUri,
        string imageFileName,
        string prompt,
        string model,
        CancellationToken cancellationToken = default)
    {
        ValidateSettings();
        var deployment = ResolveDeployment(model);
        var editUrl = BuildEditUrl(deployment);

        // Build the multipart form data
        using var content = await BuildMultipartContentAsync(originalImageUri, imageFileName, prompt, model, cancellationToken);

        using var request = new HttpRequestMessage(HttpMethod.Post, editUrl);
        request.Headers.Add("Api-Key", _settings.FOUNDRY_API_KEY);
        request.Headers.Add("x-ms-model-mesh-model-name", deployment);
        request.Content = content;

        _logger.LogInformation("Calling Foundry edits endpoint {Url} for model {Model}", editUrl, model);

        using var resp = await _httpClient.SendAsync(request, cancellationToken);
        var respText = await resp.Content.ReadAsStringAsync(cancellationToken);
        if (!resp.IsSuccessStatusCode)
        {
            _logger.LogError("Foundry returned non-success status: {Status} body: {Body}", resp.StatusCode, respText);
            throw new HttpRequestException($"Foundry returned {resp.StatusCode}: {respText}");
        }

        return ParseFirstImageBytes(respText) ?? Array.Empty<byte>();
    }

    private void ValidateSettings()
    {
        if (string.IsNullOrEmpty(_settings.FOUNDRY_ENDPOINT) ||
            string.IsNullOrEmpty(_settings.FOUNDRY_API_KEY) ||
            string.IsNullOrEmpty(_settings.FOUNDRY_API_VERSION))
        {
            throw new InvalidOperationException("Foundry settings are not configured. Please set FOUNDRY_ENDPOINT, FOUNDRY_API_KEY, and FOUNDRY_API_VERSION.");
        }
    }

    private string ResolveDeployment(string model)
    {
        var isGpt = model?.ToLower() == "gpt";
        string deployment = isGpt ? _settings.GPT_DEPLOYMENT_NAME ?? string.Empty : _settings.FLUX_DEPLOYMENT_NAME ?? string.Empty;
        if (string.IsNullOrEmpty(deployment))
        {
            throw new InvalidOperationException($"Deployment name for model '{model}' is not configured.");
        }
        return deployment;
    }

    private string BuildEditUrl(string deployment)
    {
        string basePath = $"openai/deployments/{deployment}/images";
        string paramsPart = $"?api-version={_settings.FOUNDRY_API_VERSION}";
        return new Uri(new Uri(_settings.FOUNDRY_ENDPOINT!), basePath + "/edits" + paramsPart).ToString();
    }

    private async Task<MultipartFormDataContent> BuildMultipartContentAsync(
        string originalImageUri,
        string imageFileName,
        string prompt,
        string model,
        CancellationToken cancellationToken)
    {
        var content = new MultipartFormDataContent
        {
            { new StringContent(prompt ?? string.Empty), "prompt" },
            { new StringContent("1"), "n" },
            { new StringContent("1024x1024"), "size" }
        };

        if (model?.ToLower() == "gpt")
        {
            content.Add(new StringContent("high"), "input_fidelity");
            content.Add(new StringContent("high"), "quality");
        }
        else
        {
            content.Add(new StringContent("hd"), "quality");
        }

        var imageBytes = await DownloadImageAsync(originalImageUri, cancellationToken);
        var imageStream = new MemoryStream(imageBytes); // disposed by MultipartFormDataContent when disposed
        var streamContent = new StreamContent(imageStream);
        streamContent.Headers.ContentType = new MediaTypeHeaderValue("image/jpeg");
        content.Add(streamContent, "image", Path.GetFileName(imageFileName));

        return content;
    }

    private async Task<byte[]> DownloadImageAsync(string uri, CancellationToken cancellationToken)
    {
        _logger.LogDebug("Downloading original image from {Uri}", uri);
        using WebClient webClient = new();
        return await webClient.DownloadDataTaskAsync(uri);
    }

    private byte[]? ParseFirstImageBytes(string responseJson)
    {
        try
        {
            using var jsonDoc = JsonDocument.Parse(responseJson);
            var root = jsonDoc.RootElement;
            if (!root.TryGetProperty("data", out var data) || data.ValueKind != JsonValueKind.Array)
            {
                _logger.LogWarning("Foundry response did not contain expected 'data' array: {Root}", root.ToString());
                return null;
            }

            int idx = 0;
            foreach (var item in data.EnumerateArray())
            {
                idx++;
                if (!item.TryGetProperty("b64_json", out var b64Prop))
                {
                    _logger.LogWarning("Response entry {Index} did not contain 'b64_json', skipping", idx);
                    continue;
                }
                var b64 = b64Prop.GetString();
                if (string.IsNullOrEmpty(b64))
                {
                    _logger.LogWarning("b64_json empty for entry {Index}", idx);
                    continue;
                }
                return Convert.FromBase64String(b64);
            }
        }
        catch (JsonException ex)
        {
            _logger.LogError(ex, "Failed to parse Foundry response JSON");
        }
        return null;
    }
}
