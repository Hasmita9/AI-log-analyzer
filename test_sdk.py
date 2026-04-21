from sdk.ai_log_analyzer_sdk import LogAnalyzerSDK
import logging

sdk = LogAnalyzerSDK(
    "http://127.0.0.1:5000",
    "fa44603c-23c7-48af-b308-0c22d0aad223"
)

sdk.capture_message("App started successfully")

try:
    x = 10 / 0
except Exception as e:
    sdk.capture_exception(e)

sdk.setup_auto_capture()

# Simulate real-world errors
logging.error("Database connection refused for user 123")
logging.error("Payment failed for order 456")
logging.error("Payment failed for order 456")  # duplicate (tests grouping)

logging.warning("Retrying payment service due to timeout")
logging.warning("Slow API response detected")

logging.error("CRITICAL: System crash detected in auth service")