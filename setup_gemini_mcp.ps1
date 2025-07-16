# PowerShell script to set up Gemini MCP Tool permanently
Write-Host "Setting up Gemini MCP Tool for permanent availability..." -ForegroundColor Green

# Set environment variable permanently
[Environment]::SetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "C:\Program Files\Git\bin\bash.exe", "User")
Write-Host "✅ Set CLAUDE_CODE_GIT_BASH_PATH environment variable" -ForegroundColor Green

# Set for current session
$env:CLAUDE_CODE_GIT_BASH_PATH = "C:\Program Files\Git\bin\bash.exe"

# Create Claude configuration directory
$claudeDir = "$env:APPDATA\Claude"
if (!(Test-Path $claudeDir)) {
    New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null
    Write-Host "✅ Created Claude configuration directory" -ForegroundColor Green
}

# Create MCP configuration
$mcpConfig = @{
    mcpServers = @{
        "gemini-cli" = @{
            command = "npx"
            args = @("-y", "gemini-mcp-tool")
        }
    }
} | ConvertTo-Json -Depth 3

$configPath = "$claudeDir\claude_desktop_config.json"
$mcpConfig | Out-File -FilePath $configPath -Encoding UTF8
Write-Host "✅ Created Claude MCP configuration file at: $configPath" -ForegroundColor Green

# Verify installation
Write-Host "`n📋 Verification:" -ForegroundColor Yellow
Write-Host "Environment variable: $env:CLAUDE_CODE_GIT_BASH_PATH" -ForegroundColor White
Write-Host "Config file exists: $(Test-Path $configPath)" -ForegroundColor White

Write-Host "`n✅ Setup complete!" -ForegroundColor Green
Write-Host "📋 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Restart your terminal/Claude Code session" -ForegroundColor White
Write-Host "   2. Test with: claude mcp" -ForegroundColor White
Write-Host "   3. Verify with: /mcp in Claude Code" -ForegroundColor White
Write-Host "   4. Use gemini-cli commands in Claude Code" -ForegroundColor White