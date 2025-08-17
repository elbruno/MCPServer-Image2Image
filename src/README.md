# MCP Image2Image (C#)

This README focuses on the C# solution contained in `src/`. It documents the projects, how they interact, configuration, how to run locally (including the AppHost which provisions an Azurite storage emulator), how to call the MCP tool, tests, packaging, and recommended next steps.

## Contents

- McpImage2ImageCs (main MCP server web app)
- McpImage2ImageCs.AppHost (development AppHost that provisions Azurite storage emulator)
- McpImage2ImageCs.ServiceDefaults (shared startup defaults: OpenTelemetry, health checks, service discovery)
- McpImage2ImageCs.Tests (unit tests)

## Purpose

The C# projects demonstrate a Model Context Protocol (MCP) server that exposes an image-to-image tool. The tool accepts an input image URI and a prompt, calls a Foundry/OpenAI-style images edits endpoint to produce an edited/generated image (expected as base64 in the response), stores both the original and generated images in Azure Blob Storage, and returns URLs to both images.

## Key files and responsibilities

- `Program.cs` (McpImage2ImageCs)
  - Configures the web application and registers the MCP server and tools.
  - Registers an HTTP client for Foundry, binds `FoundrySettings`, and registers `FoundryClient` as a singleton.
  - Adds an Azure BlobServiceClient and a `BlobContainerClient` for the `genimageblobs` container.

- `Services/FoundryClient.cs`
  - Builds a multipart/form-data POST to the Foundry edits endpoint.
  - Adds required headers (`Api-Key`, `x-ms-model-mesh-model-name`) and `api-version` query.
  - Downloads the original image (currently using `WebClient`), sends the request, parses JSON, and extracts `data[*].b64_json` (base64 image) for the first returned image.
  - Throws if required settings are missing.

- `Tools/ImageToImageTool.cs`
  - MCP tool method `ConvertOrGenerateImage`.
  - Downloads the input image, uploads the original image to blob storage (`GUID-original.png`), calls `FoundryClient.EditImageAsync` to create an edited image, uploads the generated image (`GUID-generated.png`), and returns a `GeneratedImageResponse` with blob URLs.

- `Settings/FoundrySettings.cs` — config model for Foundry settings.
- `Models/GeneratedImageResponse.cs` — DTO returned by the tool.
- `AppHost.cs` (McpImage2ImageCs.AppHost)
  - Provisions Azurite emulated storage and a `genimageblobs` container, then runs the main project referencing that storage. Use this for local development and integration testing.

## Configuration

Important configuration keys (map to `FoundrySettings`):

- `FOUNDRY_ENDPOINT` — Foundry base URL (e.g., `https://your-foundry.example.com/`)
- `FOUNDRY_API_KEY` — API key for Foundry
- `FOUNDRY_API_VERSION` — API version (query param)
- `GPT_DEPLOYMENT_NAME` / `FLUX_DEPLOYMENT_NAME` — model deployment names

Azure Blob Storage configuration:

- `Program.cs` registers an Azure BlobServiceClient via `builder.AddAzureBlobServiceClient("genimageBlobs")` and expects a `BlobContainerClient` for a container named `genimageblobs`.
- When using `AppHost`, Azurite is automatically provisioned and the container created with public blob access (convenient for development).

## How to run locally

Prerequisites: .NET 8 SDK installed.

Option A — AppHost (recommended for local development)

1. From the repository root run:

   dotnet run --project src\McpImage2ImageCs.AppHost

2. AppHost will:
   - Start an Azurite emulator (configured to persist data between runs).
   - Create `genimageblobs` blob container with public blob access.
   - Start the `McpImage2ImageCs` app wired to that storage.

3. Check console output for application URLs and use those to connect with an MCP client or browse health endpoints in Development.

Option B — Run the web app directly

1. Ensure your environment provides Azure Blob Storage access (for example via `AZURE_STORAGE_CONNECTION_STRING`) or other configuration supported by `AddAzureBlobServiceClient`.
2. Run:

   dotnet run --project src\McpImage2ImageCs

3. Configure `FoundrySettings` in environment variables, appsettings, or user secrets before performing tool invocations.

## Calling the MCP tool

The tool `ConvertOrGenerateImage` expects inputs:

- `model` — string, `gpt` or `flux` (default `gpt`)
- `prompt` — transformation prompt text
- `image_uri` — public URI for the input image

Output: `GeneratedImageResponse`:

- `OriginalImageUri` / `BlobOriginalImageUri` — URL to uploaded original image in `genimageblobs`
- `BlobGeneratedImageUri` — URL to uploaded generated image in `genimageblobs`

How to invoke:

- Use an MCP client (HTTP or stdio transport). The C# app registers MCP with HTTP transport by default. The exact envelope depends on your MCP client. You can also call the tool directly from C# in tests or via custom code that references the internal types.

## Tests

- `McpImage2ImageCs.Tests` contains unit tests for `FoundryClient` parsing logic.
- Run tests with:

  dotnet test src\McpImage2ImageCs.Tests

## Packaging

- `McpImage2ImageCs.csproj` includes metadata and `.mcp/server.json` so the project can be packaged as an MCP server package (NuGet-style) if desired.

## Known issues & recommendations

- `WebClient` is used in `FoundryClient` and `ImageToImageTool` for downloads; it is marked obsolete. Replace with `HttpClient` for modern, async-friendly downloads.
- The AppHost sets the blob container to public access for convenience during development. For production use, change to private access and serve files via SAS tokens or a proxy.
- Improve Foundry response robustness: support different JSON shapes or binary responses.

## Next steps (suggested)

- Replace WebClient with HttpClient (safe refactor). Update tests accordingly.
- Add an integration test that runs AppHost, performs an end-to-end call to the MCP tool, and validates uploaded blob content.
- Provide a sample MCP client (C# or Python) demonstrating an HTTP-based tool invocation.

If you'd like, I can implement one of the next steps (for example, replace WebClient with HttpClient across the codebase and update the tests). Tell me which you'd like me to do next.
