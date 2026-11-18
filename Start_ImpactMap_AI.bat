
@echo off
title ImpactMap AI

cd /d "C:\Users\Lenovo\impactmap-ai"

call venv312\Scripts\activate.bat

python -m streamlit run app.py

pause
