@echo off
cd /d "%~dp0"
echo ==============================================
echo Pushing latest SmartyNotes updates to GitHub...
echo ==============================================
echo.
git add .
git commit -m "Add root entrypoint and Vercel configuration"
git push origin main
echo.
echo ==============================================
echo PUSH COMPLETED!
echo Now check your Vercel dashboard for the new build.
echo ==============================================
pause
