# mi_py_dcm_aligner
Library for finding the biggest object in DICOM images and align them to global coordinate axes


# API Call
curl -X POST -H "Content-Type: application/json" -d @var/align_args.json http://127.0.0.1:8000/align -o var/align_results.json

in powershell:
Invoke-RestMethod -Uri http://127.0.0.1:8000/align -Method Post -ContentType "application/json" -Body (Get-Content -Path "var/align_args.json" -Raw) | Out-File -FilePath "var/align_results.json"
