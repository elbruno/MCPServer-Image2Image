var builder = DistributedApplication.CreateBuilder(args);

var genimageStorage = builder.AddAzureStorage("genimageStorage")
       .RunAsEmulator(azurite =>{
           azurite.WithDataVolume();
           azurite.WithLifetime(ContainerLifetime.Persistent);
       }); 
var genimageBlobs = genimageStorage.AddBlobs("genimageBlobs");


var mcpimage2imagecs = builder.AddProject<Projects.McpImage2ImageCs>("mcpimage2imagecs")
    .WaitFor(genimageBlobs)
    .WithReference(genimageBlobs)
    .WithExternalHttpEndpoints();

builder.Build().Run();
