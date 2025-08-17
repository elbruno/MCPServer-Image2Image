using McpImage2ImageCs.Settings;
using Microsoft.Extensions.Options;
using System.Net.Http.Headers;
using System.Text.Json;

namespace McpImage2ImageCs.Services;

public class FoundryClient : IFoundryClient
{
    private readonly HttpClient _httpClient;
    private readonly FoundrySettings _settings;
    private readonly ILogger<FoundryClient> _logger;

    public FoundryClient(IHttpClientFactory httpClientFactory, IOptions<FoundrySettings> settings, ILogger<FoundryClient> logger)
    {
        _httpClient = httpClientFactory.CreateClient("FoundryClient");
        _settings = settings.Value;
        _logger = logger;
    }

    public async Task<List<string>> EditImageAsync(string imagePath, string prompt, string model, CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrEmpty(_settings.FOUNDRY_ENDPOINT) || string.IsNullOrEmpty(_settings.FOUNDRY_API_KEY) || string.IsNullOrEmpty(_settings.FOUNDRY_API_VERSION))
        {
            throw new InvalidOperationException("Foundry settings are not configured. Please set FOUNDRY_ENDPOINT, FOUNDRY_API_KEY, and FOUNDRY_API_VERSION.");
        }

        string deployment = model?.ToLower() == "gpt" ? _settings.GPT_DEPLOYMENT_NAME ?? string.Empty : _settings.FLUX_DEPLOYMENT_NAME ?? string.Empty;
        if (string.IsNullOrEmpty(deployment))
        {
            throw new InvalidOperationException($"Deployment name for model '{model}' is not configured.");
        }

        string basePath = $"openai/deployments/{deployment}/images";
        string paramsPart = $"?api-version={_settings.FOUNDRY_API_VERSION}";
        string editUrl = new Uri(new Uri(_settings.FOUNDRY_ENDPOINT), basePath + "/edits" + paramsPart).ToString();

        using var content = new MultipartFormDataContent();

        content.Add(new StringContent(prompt ?? ""), "prompt");
        content.Add(new StringContent("1"), "n");
        content.Add(new StringContent("1024x1024"), "size");

        if (model?.ToLower() == "gpt")
        {
            content.Add(new StringContent("high"), "input_fidelity");
            content.Add(new StringContent("high"), "quality");
        }
        else
        {
            content.Add(new StringContent("hd"), "quality");
        }

        var fileStream = File.OpenRead(imagePath);
        var streamContent = new StreamContent(fileStream);
        streamContent.Headers.ContentType = new MediaTypeHeaderValue("image/png");
        content.Add(streamContent, "image", Path.GetFileName(imagePath));

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

        using var jsonDoc = JsonDocument.Parse(respText);
        var root = jsonDoc.RootElement;

        var outDir = _settings.GeneratedDir ?? Path.Combine(AppContext.BaseDirectory, "generated");
        Directory.CreateDirectory(outDir);

        var saved = new List<string>();

        if (root.TryGetProperty("data", out var data) && data.ValueKind == JsonValueKind.Array)
        {
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

                var bytes = Convert.FromBase64String(b64);
                var filename = Path.Combine(outDir, $"{DateTime.Now:yyyyMMdd_HHmmss}_" + model + $"_{idx}.png");
                await File.WriteAllBytesAsync(filename, bytes, cancellationToken);
                _logger.LogInformation("Saved generated image: {File}", filename);
                saved.Add(filename);
            }
        }
        else
        {
            _logger.LogWarning("Foundry response did not contain expected 'data' array: {Root}", root.ToString());
        }

        return saved;
    }
}
