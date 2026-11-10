# Deploy Bold BI (single container) on an E2B sandbox

1. `python3 -m venv venv && source venv/bin/activate`
2. `pip install -r requirements.txt`
3. `export E2B_API_KEY="<your key>"`
4. `python build_template.py`   (builds template `boldbi-docker`: 4 CPU, 8 GB RAM)
5. `export E2B_TEMPLATE=boldbi-docker`
6. `python deploy_boldbi.py`     (prints the public URL)
