using Azure.Storage.Blobs;
using Azure.Storage.Blobs.Models;
using McpImage2ImageCs.Models;
using McpImage2ImageCs.Services;
using ModelContextProtocol.Server;
using System.ComponentModel;
using System.Net;

[McpServerToolType]
public static class ImageToImageTool
{
    [McpServerTool, Description("Converts or generates an image using a specific model ('gpt' by default or 'flux') and a prompt with the image conversion or generation options. The tool receives the image uri.")]
    public static async Task<GeneratedImageResponse> ConvertOrGenerateImage(
        IMcpServer thisServer,
        FoundryClient foundry,
        BlobContainerClient blobContainerClient,
        string model = "gpt",
        string? prompt = null,
        string? image_uri = null,
        CancellationToken cancellationToken = default)
    {
        model = (model ?? "gpt").ToLowerInvariant();
        prompt ??= "update this image to be set in a pirate era";

        Console.Error.WriteLine($"[ImageToImageTool] model={model} prompt={(prompt.Length > 60 ? prompt[..60] + "..." : prompt)}");

        // Generate temp file names
        var (tempFileNameOriginal, tempFileNameGenerated) = GenerateTempFileNames();

        // Ensure container exists and is public
        await EnsureContainerAsync(blobContainerClient);

        // Download original image
        var originalImageBytes = await DownloadImageBytesAsync(image_uri);

        // Upload original image
        var blobUrlOriginal = await UploadBytesAsync(blobContainerClient, tempFileNameOriginal, originalImageBytes, "Original");

        // Generate / edit the image
        var generatedImageBytes = await foundry.EditImageAsync(image_uri!, tempFileNameOriginal, prompt, model, cancellationToken);

        // Upload generated image
        var blobUrlGenerated = await UploadBytesAsync(blobContainerClient, tempFileNameGenerated, generatedImageBytes, "Generated");

        return new GeneratedImageResponse
        {
            OriginalImageUri = blobUrlOriginal,
            BlobOriginalImageUri = blobUrlOriginal,
            BlobGeneratedImageUri = blobUrlGenerated
        };
    }

    private static (string original, string generated) GenerateTempFileNames()
    {
        var tmpGuid = Guid.NewGuid().ToString();
        var original = Path.Combine(tmpGuid + "-original.png");
        var generated = Path.Combine(tmpGuid + "-generated.png");
        return (original, generated);
    }

    private static async Task EnsureContainerAsync(BlobContainerClient blobContainerClient)
    {
        await blobContainerClient.CreateIfNotExistsAsync(PublicAccessType.Blob);
        await blobContainerClient.SetAccessPolicyAsync(PublicAccessType.Blob);
    }

    private static async Task<byte[]> DownloadImageBytesAsync(string? imageUri)
    {
        if (string.IsNullOrWhiteSpace(imageUri))
        {
            throw new ArgumentException("No image_uri provided. Please provide a valid image URI.");
        }

        Console.Error.WriteLine($"[ImageToImageTool] Downloading image from URI: {imageUri}");
        using WebClient webClient = new();
        var bytes = await webClient.DownloadDataTaskAsync(imageUri);
        Console.Error.WriteLine($"[ImageToImageTool] Downloaded image size: {bytes.Length} bytes");
        return bytes;
    }

    private static async Task<string> UploadBytesAsync(BlobContainerClient container, string blobName, byte[] bytes, string label)
    {
        var blobClient = container.GetBlobClient(blobName);
        using MemoryStream ms = new(bytes);
        await blobClient.UploadAsync(ms, overwrite: true);
        var url = blobClient.Uri.ToString();
        Console.WriteLine($"[ImageToImageTool] Uploaded {label} image to blob storage: {url}");
        return url;
    }
}