using Azure.Storage.Blobs;
using McpImage2ImageCs.Services;
using ModelContextProtocol.Server;
using System.ComponentModel;
using System.Net;

[McpServerToolType]
public static class ImageToImageTool
{
    [McpServerTool, Description("Converts or generates an image using a specific model ('gpt' by default or 'flux') and a prompt with the image conversion or generation options. The tool receives the image uri.")]
    public static async Task<string> ConvertOrGenerateImage(
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

        // generate a temporary file names using a guid and the .png extension
        var tmpGuid = Guid.NewGuid().ToString();
        var tempFileNameOriginal = Path.Combine(tmpGuid + "-original.png");
        var tempFileNameGenerated = Path.Combine(tmpGuid + "-generated.png");
        var blobClient = blobContainerClient.GetBlobClient(tempFileNameOriginal);

        // open a memory stream for the original image, and it's references using the uri
        byte[] image_bytes;
        if (!string.IsNullOrEmpty(image_uri))
        {
            // If image_uri is provided, download the image from the URI
            Console.Error.WriteLine($"[ImageToImageTool] Downloading image from URI: {image_uri}");
            using WebClient webClientOriginal = new WebClient();
            image_bytes = await webClientOriginal.DownloadDataTaskAsync(image_uri);
            Console.Error.WriteLine($"[ImageToImageTool] Downloaded image size: {image_bytes.Length} bytes");
        }
        else
        {
            // If no image_uri is provided, we expect the image to be passed as a byte array in the request body
            throw new ArgumentException("No image_uri provided. Please provide a valid image URI.");
        }

        using MemoryStream memoryStream = new(image_bytes);
        await blobClient.UploadAsync(memoryStream);

        //get the original image blob URL
        var blobUrlOriginal = blobClient.Uri.ToString();
        Console.WriteLine($"[ImageToImageTool] Uploaded Original image to blob storage: {blobUrlOriginal}");

        // convert / generate the image
        var foundryGeneratedImage = await foundry.EditImageAsync(memoryStream, tempFileNameOriginal, prompt, model, cancellationToken);
        Console.WriteLine($"[ImageToImageTool] completed. Generated Image: {foundryGeneratedImage}");

        // open a memory stream for the generated image
        using WebClient webClientGenerated = new WebClient();
        var generated_image_bytes = await webClientGenerated.DownloadDataTaskAsync(foundryGeneratedImage);
        using MemoryStream generatedImageStream = new(generated_image_bytes);
        var generatedBlobClient = blobContainerClient.GetBlobClient(tempFileNameGenerated);
        await generatedBlobClient.UploadAsync(generatedImageStream);
        var blobUrlGenerated = generatedBlobClient.Uri.ToString();
        Console.WriteLine($"[ImageToImageTool] Uploaded Generated image to blob storage: {blobUrlGenerated}");

        return blobUrlGenerated;
    }
}