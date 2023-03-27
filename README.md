# robobot be jank
ASDLKJAH!L!H@#K!@#H!@#!@#

## Setup
- Clone repository
- Create a venv (`py/python -m venv venv`)
- Activate it (`source ./venv/bin/activate / .\venv\Scripts\activate`)
- `pip install -r requirements.txt`
- Create a file called `auth.py` with the following contents:
    ```python
token: str = "<BOT TOKEN>"
log_id: int = <LOGGING WEBHOOK ID>
err_id: int = <ERROR LOGGING WEBHOOK ID>
```
- `py/python bot.py`