@echo off
echo ==========================================
echo   MichaWeb - Deploy All Sites to Netlify
echo ==========================================
echo.

echo [1/5] Deploying Agency Site (my-agency)...
cd /d "%~dp0my-agency"
netlify deploy --prod --dir=. --site-name=michaweb-agency 2>nul || netlify deploy --prod --dir=.
echo.

echo [2/5] Deploying Fresh Cuts Barbershop...
cd /d "%~dp0sites\fresh-cuts-barber"
netlify deploy --prod --dir=. --site-name=freshcuts-demo 2>nul || netlify deploy --prod --dir=.
echo.

echo [3/5] Deploying Elite Yard Services...
cd /d "%~dp0sites\elite-yard"
netlify deploy --prod --dir=. --site-name=eliteyard-demo 2>nul || netlify deploy --prod --dir=.
echo.

echo [4/5] Deploying Primo Lawn Service...
cd /d "%~dp0sites\primo-lawn"
netlify deploy --prod --dir=. --site-name=primolawn-demo 2>nul || netlify deploy --prod --dir=.
echo.

echo [5/5] Deploying Bella's Italian Kitchen...
cd /d "%~dp0templates\restaurant"
netlify deploy --prod --dir=. --site-name=bellas-kitchen-demo 2>nul || netlify deploy --prod --dir=.
echo.

echo ==========================================
echo   All sites deployed! Check URLs above.
echo ==========================================
pause
