@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

:: --- 基础文件夹准备 ---
if not exist error mkdir error

echo ===================================
echo [1] 正常评测模式 (生成新数据)
echo [2] 错误重测模式 (手动选择旧数据)
set /p mode="请选择模式 [1/2]: "

if "%mode%"=="2" goto retry_menu

:: --- 正常模式设置 ---
set /p total_rounds="[1/2] 输入数据组数: "
set /p repeat_per_data="[2/2] 每组重复次数: "
set curr_round=1
goto start_judge

:: --- 错误重测菜单 ---
:retry_menu
echo.
echo ======= 可重测的错误用例列表 =======
set count=0
for /d %%d in (error\case_*) do (
    set /a count+=1
    set "folder_list[!count!]=%%d"
    echo [!count!] %%d
)

if %count%==0 (
    echo [!] error 文件夹下没有找到任何错误记录。
    pause
    exit /b
)

set /p choice="请选择要重测的编号 (1-%count%): "
set "target_folder=!folder_list[%choice%]!"

if "!target_folder!"=="" (
    echo [!] 输入无效。
    goto retry_menu
)

set /p repeat_per_data="请输入重测次数: "
echo 正在准备重测: !target_folder!
goto start_judge

:: --- 主执行逻辑 ---
:start_judge
set pass_count=0
set time_limit=180
set /a ms_limit=time_limit*1000

if "%mode%"=="2" goto retry_execute

:data_loop
if %curr_round% GTR %total_rounds% goto summary
echo --- Data Group %curr_round% ---
python generator.py > test.txt
if errorlevel 1 (echo [ERROR] Generator Failed & goto summary)

set curr_repeat=1
:run_loop
if %curr_repeat% GTR %repeat_per_data% goto next_data
call :execute_and_check "Group%curr_round%" %curr_repeat%
set /a curr_repeat+=1
goto run_loop

:next_data
set /a curr_round+=1
goto data_loop

:retry_execute
copy /y "!target_folder!\input.txt" test.txt >nul
set curr_repeat=1
:retry_run_loop
if %curr_repeat% GTR %repeat_per_data% goto summary
call :execute_and_check "Retry" %curr_repeat%
set /a curr_repeat+=1
goto retry_run_loop

:: --- 核心执行与校验函数 ---
:execute_and_check
set "tag=%~1-Run%~2"
echo [%tag%] Running...

set "ps_cmd=$p=Start-Process java -ArgumentList '-jar src.jar' -RedirectStandardInput 'test.txt' -RedirectStandardOutput 'out.txt' -NoNewWindow -PassThru; if(-not $p.WaitForExit(%ms_limit%)){Stop-Process -Id $p.Id -Force; exit 124} exit $p.ExitCode"

powershell -NoProfile -Command "%ps_cmd%"
set exit_code=%errorlevel%

if %exit_code% EQU 124 (set "err_type=TLE" & goto handle_err)
if %exit_code% NEQ 0 (set "err_type=RE_%exit_code%" & goto handle_err)

python checker.py test.txt < out.txt
if errorlevel 1 (set "err_type=WA" & goto handle_err)

echo [Result] Accepted
set /a pass_count+=1
exit /b 0

:handle_err
echo [ERROR] %err_type%
:: 创建独立的错误文件夹
set "ts=%time:~0,2%%time:~3,2%%time:~6,2%"
set "ts=%ts: =0%"
set "err_dir=error\case_%date:~5,2%%date:~8,2%_%ts%_%err_type%"
mkdir "%err_dir%"

copy /y test.txt "%err_dir%\input.txt" >nul
if exist out.txt copy /y out.txt "%err_dir%\output.txt" >nul
echo Error: %err_type% > "%err_dir%\info.txt"
echo Tag: %tag% >> "%err_dir%\info.txt"

echo [Saved] 详情已保存至 %err_dir%
exit /b 1

:summary
echo ===================================
echo 评测结束。本次通过次数: %pass_count%
echo ===================================
pause