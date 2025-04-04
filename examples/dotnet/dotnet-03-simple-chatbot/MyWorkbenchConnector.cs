// Copyright (c) Microsoft. All rights reserved.

using System.Text.Json;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.SemanticWorkbench.Connector;

namespace AgentExample;

internal sealed class MyWorkbenchConnector : WorkbenchConnector<MyAgentConfig>
{
    private readonly IServiceProvider _sp;
    private readonly IConfiguration _appConfig;

    public MyWorkbenchConnector(
        IServiceProvider sp,
        IConfiguration appConfig,
        IAgentServiceStorage storage,
        IServer httpServer,
        ILoggerFactory? loggerFactory = null)
        : base(
            workbenchConfig: appConfig.GetSection("Workbench").Get<WorkbenchConfig>(),
            defaultAgentConfig: appConfig.GetSection("Agent").Get<MyAgentConfig>(),
            storage: storage,
            httpServer: httpServer,
            logger: loggerFactory?.CreateLogger<MyWorkbenchConnector>() ?? new NullLogger<MyWorkbenchConnector>())
    {
        this._sp = sp;
        this._appConfig = appConfig;
    }

    /// <inheritdoc />
    public override async Task CreateAgentAsync(
        string agentId,
        string? name,
        object? configData,
        CancellationToken cancellationToken = default)
    {
        if (this.GetAgent(agentId) != null) { return; }

        this.Log.LogDebug("Creating agent '{0}'", agentId);

        MyAgentConfig config = this.DefaultAgentConfig;
        if (configData != null)
        {
            var newCfg = JsonSerializer.Deserialize<MyAgentConfig>(JsonSerializer.Serialize(configData));
            if (newCfg != null) { config = newCfg; }
        }

        // Instantiate using .NET Service Provider so that dependencies are automatically injected
        var agent = ActivatorUtilities.CreateInstance<MyAgent>(
            this._sp,
            agentId, // agentId
            name ?? agentId, // agentName
            config, // agentConfig
            this._appConfig // appConfig
        );

        await agent.StartAsync(cancellationToken).ConfigureAwait(false);
        this.Agents.TryAdd(agentId, agent);
    }
}
