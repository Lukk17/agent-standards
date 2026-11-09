@echo off
rem run.cmd: the quality loop wrapper around Robert C. Martin's crapper, dryer and mutator, for Windows.
rem Usage: .metrics\tools\run.cmd measure, mutate [--changed] or summary [--limit N]
rem Exit codes: 0 done, 1 a tool or a setup step failed, 2 usage error or no Python 3.11, 3 a mutant survived.
rem Needs Python 3.11 or newer as python on PATH or through the py launcher.
setlocal
set "QUALITY_LOOP_RUN=%~dp0run.py"
python -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1 && goto with_python
py -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1 && goto with_py
echo quality-loop: needs Python 3.11 or newer as python on PATH or through the py launcher. 1>&2
exit /b 2
:with_python
python "%QUALITY_LOOP_RUN%" %*
exit /b %ERRORLEVEL%
:with_py
py -3 "%QUALITY_LOOP_RUN%" %*
exit /b %ERRORLEVEL%
