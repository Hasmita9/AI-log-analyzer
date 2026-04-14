from sdk.ai_log_analyzer_sdk import LogAnalyzerSDK
import logging

sdk = LogAnalyzerSDK(
    "http://127.0.0.1:5000",
    "c59d4085-f795-4a11-b67e-8ca55958b6ab"
)

sdk.capture_message("App started successfully")

try:
    x = 10 / 0
except Exception as e:
    sdk.capture_exception(e)

sdk.setup_auto_capture()

logging.error("This is a test error from logging")
logging.warning("This is a test warning")
logging.info("This is an info message")