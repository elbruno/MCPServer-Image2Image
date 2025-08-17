## Image2Image MCP Server - Implementation Plan (C#)

Goal
------

Create a C# implementation, for the project under `src/McpImage2ImageCs`, that reproduces the features present in `mcp_server.py` (image-to-image tool) using the latest C# MCP SDK (<https://github.com/modelcontextprotocol/csharp-sdk>). This document maps Python features to C# components, lists required packages, describes the concrete files and classes to add, and provides a step-by-step implementation and testing plan.

Scope (what to port)
---------------------

- MCP tool named `image2image` that accepts:
  - `model` (string, "gpt" or "flux")
  - `prompt` (string)
  - `image_base64` (string) OR `image_path` (server-local path)
- Environment configuration: `FOUNDRY_ENDPOINT`, `FOUNDRY_API_KEY`, `FOUNDRY_API_VERSION`, `FLUX_DEPLOYMENT_NAME`, `GPT_DEPLOYMENT_NAME` (same names as the Python server)
- Call Foundry images/edit endpoint using a multipart request, including file + form fields
- Decode base64 images to a temporary file when image is passed as `image_base64`
- Save resulting Base64 images from Foundry response to `generated/` with timestamped filenames
- Logging, validation, and helpful errors
- Clean up temporary files
- Expose the tool via MCP server so clients can discover and call it

High-level mapping to the C# MCP SDK
------------------------------------

- MCP Server host: use `Host.CreateApplicationBuilder(args)` and the `ModelContextProtocol` server package
- Register tools with `AddMcpServer()` and `.WithToolsFromAssembly()` (or explicit tool registration)
- Tools: a static class with `[McpServerToolType]` and a method marked `[McpServerTool]` to provide the `image2image` tool
- Dependency injection: register a `FoundryClient` service (typed HttpClient) to encapsulate Foundry calls
- Configuration: bind a settings POCO to `IConfiguration` to expose env vars
- Logging: use `ILogger<T>` injected into tools/services
- File handling & images: use `System.IO` for temp files + `SixLabors.ImageSharp` (recommended) for image decoding & saving

Required NuGet packages
-----------------------

- ModelContextProtocol (preview) - core SDK
- Microsoft.Extensions.Hosting
- Microsoft.Extensions.Configuration.EnvironmentVariables (already transitively available via hosting)
- Microsoft.Extensions.Http (for typed HttpClient registration)
- SixLabors.ImageSharp (for robust image decoding & saving)
- System.Text.Json (if needed for JSON parsing; usually part of .NET SDK)

Proposed new files and responsibilities
-------------------------------------

- `Settings/FoundrySettings.cs` (POCO)
  - Properties: FoundryEndpoint, FoundryApiKey, FoundryApiVersion, FluxDeploymentName, GptDeploymentName, GeneratedDir
  - Bound from `IConfiguration` (env vars)
- `Services/IFoundryClient.cs` + `Services/FoundryClient.cs`
  - Encapsulates calls to Foundry images endpoint
  - Public method: Task<List<string>> EditImageAsync(string imagePath, string prompt, string model, CancellationToken ct)
  - Uses typed HttpClient (named or typed) and `MultipartFormDataContent` to POST image + fields
  - Parses the response JSON, extracts `data[*].b64_json`, decodes and writes files to `generated/`
  - Returns saved file paths
  - Throws informative exceptions on HTTP non-success or invalid responses
- `Tools/Image2ImageTool.cs`
  - Static class decorated with `[McpServerToolType]`
  - Exposes `[McpServerTool] public static async Task<string[]> Image2Image(IMcpServer thisServer, ILogger logger, IFoundryClient foundry, string model = "gpt", string prompt = null, string image_base64 = null, string image_path = null)`
  - Implements logic to prefer `image_base64` over `image_path`, create a temp file when needed, call `foundry.EditImageAsync(...)`, and clean up temp file
  - Use `thisServer` or `ILogger` to do sampling or additional interactions if needed
- `Program.cs` (or modifications to `Program.cs`)
  - Wire up host builder, configuration (environment variables), logging, register FoundryClient (typed HttpClient), register settings, call `AddMcpServer().WithToolsFromAssembly()` and run
- `Tests/FoundryClientTests.cs` and `Tests/Image2ImageToolTests.cs`
  - Unit test FoundryClient by mocking HttpMessageHandler and verifying request composition and saved files
  - Unit test Image2ImageTool behavior for base64 path selection, error handling, and temp file cleanup

Detailed design notes
---------------------

1) Configuration
   - Use env var names identical to the Python project. Bind them in `Program.cs`:

```csharp
builder.Services.Configure<FoundrySettings>(builder.Configuration);
```

- Provide default `GeneratedDir` = `Path.Combine(AppContext.BaseDirectory, "generated")` if not supplied

2) Foundry HTTP call
   - Endpoint path mirrors Python: `${FOUNDRY_ENDPOINT}/openai/deployments/{deployment}/images/edits?api-version={FOUNDRY_API_VERSION}`
   - Headers: `Api-Key: {FOUNDRY_API_KEY}`, `x-ms-model-mesh-model-name: {deployment}`
   - Content:
     - `MultipartFormDataContent` with:
       - `image` as `StreamContent` or `ByteArrayContent` with ContentDisposition name `image` and filename
       - string form fields for `prompt`, `n`, `size`, and quality/fidelity fields depending on model
   - Response: JSON with `data` array and each element with `b64_json`; decode each and write to disk with timestamped filenames

3) Image decoding & writing
   - Use `Convert.FromBase64String(...)` + `Image.Load(...)` from ImageSharp to create and save PNG
   - Create `generated` directory if missing

4) Temporary image handling
   - For provided `image_base64`, write bytes to a temp file via `Path.GetTempFileName()` then `File.WriteAllBytes(tempPath, bytes)` with extension `.png`.
   - Ensure deletion in finally block. Log any cleanup failures but don't swallow upstream exceptions unless appropriate.

5) MCP tool signature & registration
   - Use `[McpServerTool]` attribute on the static method. The SDK will expose the method to clients when `.WithToolsFromAssembly()` is used.
   - Method should return `string[]` or `List<string>` for saved paths. Alternatively, return a JSON structure with `paths` array if desired.

6) Logging & errors
   - Use `ILogger<T>` and consistent log levels
   - For HTTP errors, throw `McpException` or a normal exception so the protocol surfaces the error to the client; include Foundry response text when possible

Step-by-step implementation plan
--------------------------------

```markdown
- [ ] Step 1: Add FoundrySettings POCO and bind configuration in `Program.cs`.
- [ ] Step 2: Add `IFoundryClient` + `FoundryClient` using typed HttpClient; implement `EditImageAsync`.
- [ ] Step 3: Add `Image2ImageTool` static class with `[McpServerToolType]` and `[McpServerTool]` method.
- [ ] Step 4: Register services and tools in `Program.cs` and verify server starts locally.
- [ ] Step 5: Implement unit tests for `FoundryClient` and `Image2ImageTool`.
- [ ] Step 6: Add CI configuration: `dotnet restore`, `dotnet build`, `dotnet test`.
- [ ] Step 7: Manual smoke test: call the tool via an MCP client (or `McpServerFactory` stdio transport) and verify generated/ files.
```

Testing and QA
--------------

- Unit tests:
  - Mock `HttpMessageHandler` to ensure `FoundryClient` posts expected URL, headers, and multipart content.
  - Verify base64 decoding behavior: when Foundry returns b64_json, files are saved and paths returned.
  - Test temp file creation + cleanup for `image_base64` branch.
- Integration / smoke tests:
  - Start the MCP server locally and call the `image2image` tool using the C# MCP client sample (or `npx @modelcontextprotocol/server-everything` as a client) with a small test image.
  - Verify `generated/` contains expected output files and logs show successful calls.

CI and developer workflow
------------------------

- Add a GitHub Actions workflow that runs on push and PR for `main`:
  - Steps: checkout, setup dotnet, `dotnet restore`, `dotnet build --no-restore`, `dotnet test --no-build`
- Add a `scripts/` helper for local development to run the server and to run the sample client (if desired).

Notes, edge cases and recommendations
------------------------------------

- Use ImageSharp rather than System.Drawing for cross-platform reliable image ops.
- Consider adding request/response timeouts and retry policies for network resilience (HttpClientFactory Polly policies).
- Consider secrets handling: encourage use of Azure Key Vault or user secrets instead of raw env vars in production.
- Validate the Foundry response schema carefully: not all responses will include `b64_json` and there may be errors embedded; handle gracefully.

Quick implementation timeline (rough)
-----------------------------------

- Design & wiring (1 day) — settings, DI, Program.cs changes
- FoundryClient (1 day) — implement and unit test
- Tool & integration test (0.5–1 day)
- CI, docs, polish (0.5 day)

Acceptance criteria
-------------------

- The `image2image` MCP tool is discoverable by MCP clients.
- The tool accepts the same parameters and behavior as the Python version (model selection, prompt, base64/file input).
- Files produced by Foundry are saved to `generated/` with timestamped names and returned to the caller.
- Temporary files are cleaned up after processing.

Follow-ups (optional)
---------------------

- Add telemetry/metrics for call count, latency, success/failure
- Add configurable concurrency limits and request size limits
- Add robust validation of prompt and model inputs and map model strings to strongly-typed enums

References
----------

- C# MCP SDK: <https://github.com/modelcontextprotocol/csharp-sdk>
- MCP protocol: <https://spec.modelcontextprotocol.io/>

---
Created to map `mcp_server.py` features into a concrete, testable C# implementation plan for `src/McpImage2ImageCs`.
