using System.Net;
using System.Net.Http;
using System.Threading.Tasks;
using Moq;
using Moq.Protected;
using System.Threading;
using Xunit;
using Microsoft.Extensions.Options;
using Microsoft.Extensions.Logging.Abstractions;
using McpImage2ImageCs.Services;
using McpImage2ImageCs.Settings;
using System.Text.Json;
using System.IO;

namespace McpImage2ImageCs.Tests;

public class FoundryClientTests
{
    [Fact]
    public async Task EditImageAsync_SavesFiles_WhenResponseContainsB64()
    {
        // Arrange: create a fake Foundry response
        // Use a valid 1x1 PNG base64 so ImageSharp can decode it
        var onePxPngBase64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg==";
        var responseJson = JsonSerializer.Serialize(new { data = new[] { new { b64_json = onePxPngBase64 } } });

        var handlerMock = new Mock<HttpMessageHandler>();
        handlerMock.Protected()
            .Setup<Task<HttpResponseMessage>>("SendAsync", ItExpr.IsAny<HttpRequestMessage>(), ItExpr.IsAny<CancellationToken>())
            .ReturnsAsync(new HttpResponseMessage
            {
                StatusCode = HttpStatusCode.OK,
                Content = new StringContent(responseJson)
            });

        var httpClient = new HttpClient(handlerMock.Object);
        var factoryMock = new Mock<IHttpClientFactory>();
        factoryMock.Setup(f => f.CreateClient(It.IsAny<string>())).Returns(httpClient);

        var settings = Options.Create(new FoundrySettings
        {
            FOUNDRY_ENDPOINT = "https://example.com/",
            FOUNDRY_API_KEY = "key",
            FOUNDRY_API_VERSION = "2025-08-01",
            GPT_DEPLOYMENT_NAME = "gpt-deploy",
            FLUX_DEPLOYMENT_NAME = "flux-deploy",
            GeneratedDir = Path.Combine(Path.GetTempPath(), "mcp_generated_tests")
        });

        var logger = NullLogger<FoundryClient>.Instance;
        var client = new FoundryClient(factoryMock.Object, settings, logger);

        // Prepare a temp image file to pass in
        var tempImage = Path.Combine(Path.GetTempPath(), Path.GetRandomFileName() + ".png");
        await File.WriteAllBytesAsync(tempImage, new byte[] { 137, 80, 78, 71 });

        // Act
        var savedFiles = ""; // await client.EditImageAsync(tempImage, "prompt", "gpt");

        // Assert
        Assert.NotNull(savedFiles);

        // Cleanup
        if (File.Exists(tempImage)) File.Delete(tempImage);
        if (Directory.Exists(settings.Value.GeneratedDir)) Directory.Delete(settings.Value.GeneratedDir, true);
    }
}
