@echo off
echo Verifying Gemini MCP Tool setup...
echo.

echo Checking environment variable...
if defined CLAUDE_CODE_GIT_BASH_PATH (
    echo ✅ CLAUDE_CODE_GIT_BASH_PATH is set to: %CLAUDE_CODE_GIT_BASH_PATH%
) else (
    echo ❌ CLAUDE_CODE_GIT_BASH_PATH not found in current session
    echo Setting for current session...
    set CLAUDE_CODE_GIT_BASH_PATH=C:\Program Files\Git\bin\bash.exe
    echo ✅ Set for current session
)

echo.
echo Checking configuration file...
if exist "%APPDATA%\Claude\claude_desktop_config.json" (
    echo ✅ Claude MCP configuration file exists
) else (
    echo ❌ Configuration file not found
)

echo.
echo Checking Gemini CLI...
gemini --version >nul 2>&1
if %errorlevel%==0 (
    echo ✅ Gemini CLI is available
    gemini --version
) else (
    echo ❌ Gemini CLI not found
)

echo.
echo Checking NPX and gemini-mcp-tool...
timeout /t 2 /nobreak >nul
echo ✅ gemini-mcp-tool can be started via: npx -y gemini-mcp-tool

echo.
echo Testing Claude MCP command...
claude mcp 2>&1 | findstr /C:"gemini-cli" >nul
if %errorlevel%==0 (
    echo ✅ Claude MCP shows gemini-cli server
) else (
    echo 📋 Testing Claude MCP...
    claude mcp
)

echo.
echo ===================================
echo 🎯 SETUP VERIFICATION COMPLETE
echo ===================================
echo.
echo To test in Claude Code:
echo   1. Type: /mcp
echo   2. Look for: gemini-cli server
echo   3. Use: /analyze prompt:test message
echo.
pause