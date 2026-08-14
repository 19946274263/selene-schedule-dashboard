@echo off
chcp 65001 > nul
setlocal
REM ============================================================
REM  一键创建「每小时自动刷新看板」的 Windows 任务计划
REM  作用：调用 fetch_selene.py 拉取 Selene 最新排期并重新生成看板
REM  - token 有效时：自动刷新数据 + 重新生成 HTML + 同步到 deploy/
REM  - token 过期时：沿用上一次成功快照，并在看板顶部提示「token 已过期」
REM  日志：selene_sync.log
REM  取消任务：schtasks /delete /tn SeleneDashboardSync /f
REM ============================================================

set "DIR=E:\autotest\workbuddy\selene-schedule-dashboard"
if not exist "%DIR%" set "DIR=%~dp0"

set "TASK=SeleneDashboardSync"
set "PY=python"

echo 工作目录：%DIR%
echo.

schtasks /query /tn "%TASK%" >nul 2>&1
if %errorlevel%==0 (
  echo 任务 %TASK% 已存在，先删除再重建…
  schtasks /delete /tn "%TASK%" /f >nul 2>&1
)

schtasks /create /sc hourly /st 00:30 /tn "%TASK%" ^
  /tr "cmd /c cd /d \"%DIR%\" && %PY% fetch_selene.py >> \"%DIR%\selene_sync.log\" 2>&1" /f

echo.
echo [OK] 已创建每小时自动刷新任务：%TASK%
echo      日志文件：%DIR%\selene_sync.log
echo.
echo 使用前提：
echo   1) 已安装 Python 3.8+ 且在 PATH 中（否则把上面 %PY% 改成 python.exe 完整路径）
echo   2) %DIR%\selene_token.txt 中存在有效 token
echo      （token 获取：登录 Selene 网页 → DevTools → Application → Local Storage →
echo        http://selene.hd123.cn:52163 → 复制 vuex 里的 token 字段）
echo.
echo 注意：本任务只刷新「本地数据 + 本地 HTML」。若要更新对外分享的公开链接，
echo   在刷新 token 后请重新运行一次部署（让 AI 助手重新 deploy，或自行发布）。
echo.
pause
