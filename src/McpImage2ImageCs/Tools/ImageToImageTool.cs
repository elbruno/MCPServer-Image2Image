using System.ComponentModel;
using ModelContextProtocol.Server;
using McpImage2ImageCs.Services;

[McpServerToolType]
public static class ImageToImageTool
{
    [McpServerTool, Description("Converts or generates an image using a specific model ('gpt' by default or 'flux') and a prompt with the image conversion or generation options.")]
    public static async Task<List<string>> ConvertOrGenerateImage(
        IMcpServer thisServer,
        IFoundryClient foundry,
        string model = "gpt",
        string? prompt = null,
        string? image_base64 = null,
        string? image_path = null,
        CancellationToken cancellationToken = default)
    {
        model = (model ?? "gpt").ToLowerInvariant();
        prompt ??= "update this image to be set in a pirate era";

        Console.Error.WriteLine($"[ImageToImageTool] model={model} prompt={(prompt.Length > 60 ? prompt[..60] + "..." : prompt)} hasBase64={!string.IsNullOrEmpty(image_base64)} image_path={image_path}");

        bool tmpCreated = false;
        string? imgPath = null;

        try
        {
            if (!string.IsNullOrEmpty(image_base64))
            {
                var comma = image_base64.IndexOf(',');
                var b64 = comma >= 0 ? image_base64[(comma + 1)..] : image_base64;
                var bytes = Convert.FromBase64String(b64);
                var temp = Path.Combine(Path.GetTempPath(), Path.GetRandomFileName() + ".png");
                await File.WriteAllBytesAsync(temp, bytes, cancellationToken);
                imgPath = temp;
                tmpCreated = true;
                Console.Error.WriteLine($"[ImageToImageTool] wrote temporary image file: {temp}");
            }
            else if (!string.IsNullOrEmpty(image_path))
            {
                var candidate = Path.GetFullPath(image_path);
                if (!File.Exists(candidate))
                {
                    Console.Error.WriteLine($"[ImageToImageTool] image_path not found: {candidate}");
                    throw new FileNotFoundException($"image_path not found: {candidate}");
                }

                imgPath = candidate;
            }
            else
            {
                Console.Error.WriteLine("[ImageToImageTool] No image provided to ImageToImageTool tool");
                throw new ArgumentException("No image provided. Please provide 'image_base64' or 'image_path'.");
            }

            var saved = await foundry.EditImageAsync(imgPath!, prompt!, model, cancellationToken);
            Console.Error.WriteLine($"[ImageToImageTool] completed, {saved.Count} files saved");
            return saved;
        }
        finally
        {
            if (tmpCreated && imgPath != null && File.Exists(imgPath))
            {
                try
                {
                    File.Delete(imgPath);
                    Console.Error.WriteLine($"[ImageToImageTool] removed temporary file: {imgPath}");
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine($"[ImageToImageTool] failed to remove temporary image file {imgPath}: {ex.Message}");
                }
            }
        }
    }
}
