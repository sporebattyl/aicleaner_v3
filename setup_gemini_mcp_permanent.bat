@echo off
echo Setting up Gemini MCP Tool for permanent availability...

REM Set environment variable permanently for current user
setx CLAUDE_CODE_GIT_BASH_PATH "C:\Program Files\Git\bin\bash.exe"
echo ✅ Set CLAUDE_CODE_GIT_BASH_PATH environment variable

REM Set for current session as well
set CLAUDE_CODE_GIT_BASH_PATH=C:\Program Files\Git\bin\bash.exe

REM Create Claude configuration directory if it doesn't exist
if not exist "%APPDATA%\Claude" (
    mkdir "%APPDATA%\Claude"
    echo ✅ Created Claude configuration directory
)

REM Create MCP configuration file
echo Creating MCP configuration file...
(
echo {
echo   "mcpServers": {
echo     "gemini-cli": {
echo       "command": "npx",
echo       "args": ["-y", "gemini-mcp-tool"]
echo     }
echo   }
echo }
) > "%APPDATA%\Claude\claude_desktop_config.json"
echo ✅ Created Claude MCP configuration file

REM Also try creating configuration in alternative location
if not exist "%USERPROFILE%\.claude" (
    mkdir "%USERPROFILE%\.claude"
)

copy "%APPDATA%\Claude\claude_desktop_config.json" "%USERPROFILE%\.claude\config.json" >nul 2>&1

echo.
echo ✅ Gemini MCP Tool setup complete!
echo.
echo Configuration locations:
echo   - %APPDATA%\Claude\claude_desktop_config.json
echo   - %USERPROFILE%\.claude\config.json
echo.
echo Next steps:
echo   1. Restart your terminal/command prompt
echo   2. Test with: claude mcp
echo   3. Verify with: /mcp in Claude Code
echo.
echo Environment variable set: CLAUDE_CODE_GIT_BASH_PATH="C:\Program Files\Git\bin\bash.exe"
pause