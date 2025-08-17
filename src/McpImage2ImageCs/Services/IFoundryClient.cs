using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace McpImage2ImageCs.Services;

public interface IFoundryClient
{
    Task<List<string>> EditImageAsync(string imagePath, string prompt, string model, CancellationToken cancellationToken = default);
}
