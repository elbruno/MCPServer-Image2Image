using System.ComponentModel;
using ModelContextProtocol.Server;
using McpImage2ImageCs.Services;
using Microsoft.Extensions.Logging;
using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;

[McpServerToolType]
public static class Image2ImageTool
{
    [McpServerTool, Description("Converts an image using Foundry (gpt or flux) and a prompt.")]
    public static async Task<List<string>> Image2Image(
        IMcpServer thisServer,
        ILogger logger,
        IFoundryClient foundry,
        string model = "gpt",
        string? prompt = null,
        string? image_base64 = null,
        string? image_path = null,
        CancellationToken cancellationToken = default)
    {
        model = (model ?? "gpt").ToLowerInvariant();
        prompt ??= "update this image to be set in a pirate era";

        logger.LogInformation("image2image called with model={Model} prompt={Prompt} hasBase64={HasBase64} image_path={Path}", model, prompt, !string.IsNullOrEmpty(image_base64), image_path);

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
                logger.LogInformation("Wrote temporary image file: {Temp}", temp);
            }
            else if (!string.IsNullOrEmpty(image_path))
            {
                var candidate = Path.GetFullPath(image_path);
                if (!File.Exists(candidate))
                {
                    logger.LogError("image_path not found: {Path}", candidate);
                    throw new FileNotFoundException($"image_path not found: {candidate}");
                }

                imgPath = candidate;
            }
            else
            {
                logger.LogError("No image provided to image2image tool");
                throw new ArgumentException("No image provided. Please provide 'image_base64' or 'image_path'.");
            }

            var saved = await foundry.EditImageAsync(imgPath!, prompt!, model, cancellationToken);
            logger.LogInformation("image2image completed, {Count} files saved", saved.Count);
            return saved;
        }
        finally
        {
            if (tmpCreated && imgPath != null && File.Exists(imgPath))
            {
                try
                {
                    File.Delete(imgPath);
                    logger.LogDebug("Removed temporary file: {File}", imgPath);
                }
                catch (Exception ex)
                {
                    logger.LogError(ex, "Failed to remove temporary image file: {File}", imgPath);
                }
            }
        }
    }
}
