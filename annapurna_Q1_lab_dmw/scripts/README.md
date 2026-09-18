# Scripts

`load_sales.py` is a GitHub-safe copy of the loader used in the exam run. It reads credentials from environment variables instead of embedding the local lab password.

Required environment variables are listed in `.env.example`.

Run from the repository root:

```powershell
py .\scripts\load_sales.py proof1
```

The input sales files should be present under `raw/` when running locally.
