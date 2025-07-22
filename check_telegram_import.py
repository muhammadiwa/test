import sys

print("Python path:", sys.path)

try:
    import telegram
    print("Telegram module path:", telegram.__file__)
    print("Telegram module attributes:", dir(telegram))
except Exception as e:
    print("Error importing telegram:", e)

try:
    from telegram import Update
    print("Update class imported successfully")
    print("Update attributes:", dir(Update))
except Exception as e:
    print("Error importing Update:", e)

try:
    from telegram.ext import Application
    print("Application class imported successfully")
    print("Application attributes:", dir(Application))
except Exception as e:
    print("Error importing Application:", e)
