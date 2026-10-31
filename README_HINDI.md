# Personal AI Life Assistant — VS Code Ready

## चालू करने का तरीका (Windows)
1. ZIP को Extract करें।
2. VS Code खोलें → **File → Open Folder** → `Personal_AI_Life_Assistant` फ़ोल्डर चुनें।
3. Python 3.10 या नया इंस्टॉल होना चाहिए।
4. `start.bat` पर double-click करें, या VS Code terminal में:
   ```powershell
   .\start.bat
   ```
5. Browser में `http://127.0.0.1:8000` खोलें।
6. पहली बार **Create account** से अपना account बनाएं। अगली बार उसी username/password से login करें।

## क्या-क्या काम करता है?
- Signup/login/logout, PBKDF2 password hashing, signed session cookie
- Per-user isolated SQLite records
- Dashboard, tasks, events, reminders, study subjects, income/expense entries, notes
- Voice input via browser Speech Recognition (browser/device support पर निर्भर)
- Voice responses via browser speech synthesis
- Search/filter, data export, account deletion
- Basic built-in assistant commands without paid API: add task, add reminder, show tasks, study/expense summaries

## जरूरी बातें
- यह local-first app है: default रूप से आपके laptop पर `assistant.db` में data रहता है।
- दूसरे device पर same account से access करने के लिए app को सुरक्षित server पर deploy करना होगा; `127.0.0.1` सिर्फ उसी device पर खुलता है।
- Passwords plain text में store नहीं होते। फिर भी यह starter app public internet पर deploy करने से पहले HTTPS, secret management, rate limiting, email-based password recovery और production security review मांगता है।
- Voice recognition Chrome/Edge जैसे supported browser में बेहतर काम कर सकती है; कुछ browsers speech recognition के लिए network service इस्तेमाल करते हैं।
- Basic assistant commands free हैं। External/advanced AI API शामिल नहीं है, इसलिए कोई paid AI key जरूरी नहीं।
- Notifications तब तक app के खुले रहने पर चलती हैं; background/push notifications के लिए hosted service और browser permission की जरूरत हो सकती है।
