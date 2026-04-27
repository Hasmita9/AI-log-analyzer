from sdk.ai_log_analyzer_sdk import LogAnalyzerSDK
import logging

sdk = LogAnalyzerSDK(
    "http://127.0.0.1:5000",
    # "http://127.0.1.2:5002",
    # "d2089b1e-908f-4bc0-a305-627e5f12e98c"
    "79bed7e4-713f-408f-b1aa-6ae690766132"
)

# sdk.capture_message("App started successfully")

# try:
#     x = 10 / 2
# except Exception as e:
#     sdk.capture_exception(e)

sdk.setup_auto_capture()

# Simulate real-world errors
# logging.error("Database connection refused for user 123")
# logging.error("Payment failed for order 456")
# logging.error("Payment failed for order 456")  # duplicate (tests grouping)

# logging.warning("Retrying payment service due to timeout")
# logging.warning("Slow API response detected")

# logging.error("CRITICAL: System crash detected in auth service")