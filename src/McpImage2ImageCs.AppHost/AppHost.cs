var builder = DistributedApplication.CreateBuilder(args);

var mcpimage2imagecs = builder.AddProject<Projects.McpImage2ImageCs>("mcpimage2imagecs")
    .WithExternalHttpEndpoints();

builder.Build().Run();
