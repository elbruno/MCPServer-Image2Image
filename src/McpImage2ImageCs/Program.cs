using Azure.Storage.Blobs;
using McpImage2ImageCs.Services;
using McpImage2ImageCs.Settings;

var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();

// Configure all logs to go to stderr (stdout is used for the MCP protocol messages when using stdio).
builder.Logging.ClearProviders();
builder.Logging.AddConsole(o => o.LogToStandardErrorThreshold = Microsoft.Extensions.Logging.LogLevel.Trace);

// Add the MCP services: use HTTP transport for web-hosted MCP server and register tools from this assembly
builder.Services
    .AddMcpServer()
    .WithHttpTransport()
    .WithToolsFromAssembly();

// Register Foundry client and settings for image2image tool
builder.Services.AddHttpClient("FoundryClient");
builder.Services.Configure<FoundrySettings>(builder.Configuration.GetSection("FoundrySettings"));
builder.Services.AddSingleton<FoundryClient>();

// get azure storage blobs
builder.AddAzureBlobServiceClient("genimageBlobs");

// add a blobContainerClient with the name "genimageBlobs" so it can be used in the tool
builder.Services.AddSingleton(sp =>
{
    var blobServiceClient = sp.GetRequiredService<BlobServiceClient>();
    return blobServiceClient.GetBlobContainerClient("genimageblobs");
});



var app = builder.Build();

app.MapDefaultEndpoints();

// Map MCP endpoints
app.MapMcp();

app.Run();
