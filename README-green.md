# Bilibili Video Downloader Green Package

This package is for end users who want to download and run the app directly on Windows.

## How to use

1. Extract the full archive
2. Make sure these items stay in the same folder:
   - `runtime/`
   - `dist/`
   - `api.py`
   - `start.bat`
   - `README-green.md`
3. Double-click `start.bat`
4. Open [http://localhost:5000](http://localhost:5000) in your browser

## Notes

- If `runtime\python.exe` is missing, you downloaded the source repository instead of the green package zip
- If Bilibili returns HTTP 412, first open the target video page in your browser and refresh it, then try again
