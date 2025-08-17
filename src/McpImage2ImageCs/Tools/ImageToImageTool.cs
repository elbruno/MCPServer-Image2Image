using Azure.Storage.Blobs;
using McpImage2ImageCs.Services;
using ModelContextProtocol.Server;
using System.ComponentModel;
using System.IO;

[McpServerToolType]
public static class ImageToImageTool
{
    [McpServerTool, Description("Converts or generates an image using a specific model ('gpt' by default or 'flux') and a prompt with the image conversion or generation options. The tool receives an images in base64 string.")]
    public static async Task<string> ConvertOrGenerateImage(
        IMcpServer thisServer,
        FoundryClient foundry,
        BlobContainerClient blobContainerClient,
        string model = "gpt",
        string? prompt = null,
        string? image_base64 = null,
        //string? image_path = null,
        CancellationToken cancellationToken = default)
    {
        model = (model ?? "gpt").ToLowerInvariant();
        prompt ??= "update this image to be set in a pirate era";

        Console.Error.WriteLine($"[ImageToImageTool] model={model} prompt={(prompt.Length > 60 ? prompt[..60] + "..." : prompt)} hasBase64={!string.IsNullOrEmpty(image_base64)} ");

        // generate a temporary file names using a guid and the .png extension
        var tmpGuid = Guid.NewGuid().ToString();
        var tempFileNameOriginal = Path.Combine(tmpGuid + "-original.png");
        var tempFileNameGenerated = Path.Combine(tmpGuid + "-generated.png");
        var blobClient = blobContainerClient.GetBlobClient(tempFileNameOriginal);

        // convert the original image64string to a byte array
        var comma = image_base64.IndexOf(',');
        var b64 = comma >= 0 ? image_base64[(comma + 1)..] : image_base64;
        var bytes = Convert.FromBase64String(b64);

        using MemoryStream memoryStream = new(bytes);
        await blobClient.UploadAsync(memoryStream);

        //get the original image blob URL
        var blobUrlOriginal = blobClient.Uri.ToString();
        Console.Error.WriteLine($"[ImageToImageTool] Uploaded Original image to blob storage: {blobUrlOriginal}");

        // convert / generate the image
        var foundryGeneratedImage = await foundry.EditImageAsync(memoryStream, tempFileNameOriginal, prompt, model, cancellationToken);
        Console.Error.WriteLine($"[ImageToImageTool] completed. Generated Image: {foundryGeneratedImage}");

        // open a memory stream for the generated image
        using MemoryStream generatedImageStream = new(Convert.FromBase64String(foundryGeneratedImage));
        // upload the generated image to blob storage
        var generatedBlobClient = blobContainerClient.GetBlobClient(tempFileNameGenerated);
                await generatedBlobClient.UploadAsync(generatedImageStream);
        // get the generated image blob URL
        var blobUrlGenerated = generatedBlobClient.Uri.ToString();
        Console.Error.WriteLine($"[ImageToImageTool] Uploaded Generated image to blob storage: {blobUrlGenerated}");

        return blobUrlGenerated;
    }
}