# ThreadWise Gen Z — Smart Wardrobe + Security

## Run on Windows / VS Code
1. Install Python 3.10+ and enable “Add Python to PATH”.
2. Extract ZIP and open the `ThreadWise_GenZ` folder in VS Code.
3. Terminal → New Terminal; run one at a time:
   ```
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python app.py
   ```
   If activation is blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate. Command Prompt can use `.venv\Scripts\activate.bat`.
4. Open http://127.0.0.1:5000 and register.

## Demo
Add a white item in Tops, black item in Bottoms, then visit Before You Buy and check Black Bottoms. Check Bags to see a possible gap. Save a suggestion to wishlist and open Security Lab. While logged in, `/api/wardrobe-summary` returns JSON.

## Cloud security concepts used
- Authentication: registration and login.
- Password hashing: Werkzeug one-way hash; raw passwords are not stored.
- User data isolation: all personal queries filter by current user ID; delete routes check ownership.
- Session cookie flags: HttpOnly and SameSite=Lax.
- Audit log: timestamped account and wardrobe events.
- SQL parameterization and basic input validation.
- Random secret key for local demo. Set a stable strong `SECRET_KEY` as an environment variable for deployment.

**Scope note:** This is a local working prototype, not hosted on AWS/Azure/GCP. It doesn't connect to shopping websites or perform image recognition/AI. Before production deployment add HTTPS, CSRF protection, rate limiting, login throttling, secure secret management, backups, monitoring and a managed database. Do not use debug mode in production.
